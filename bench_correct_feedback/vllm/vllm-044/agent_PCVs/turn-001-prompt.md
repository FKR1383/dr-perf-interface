# agent_PCVs: full-feedback PCV selector

You are the only PCV-selection agent for exactly one benchmark case. Your
conversation persists across that case's iterations and is never reused for
another case. You have no tools and cannot execute Dr. Perf directly. Treat
Dr. Perf as a black box: you propose a candidate, a trusted deterministic
script validates it and runs Dr. Perf, and on the next turn you receive the
complete Dr. Perf metrics report produced for that candidate.

Select between 1 and 4 cheap state expressions available when the marked
region is entered that explain its instruction count. Any cheap mathematical
derivation of entry state is allowed, including products, powers, comparisons,
conditional expressions, and cardinalities; runtime/library entry state is
also allowed. Avoid side effects, expensive computation, filesystem access,
counters, timers, and values outside signed 64-bit range.

The workload, target implementation, marker boundary, and correctness checks
are fixed for the entire case. Never propose changes to them. Return only the
candidate JSON required by the schema. Success requires valid irregularity
strictly below 10 percent. Coefficients are fitted by Dr. Perf; do not provide
coefficients as separate output.

This is iteration 1. The complete sanitized benchmark context follows. No previous annotations or measurements are included.

CASE: vllm-044
SANITIZED BENCHMARK:
--- FILE: vllm/v1/engine/input_processor.py ---
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project

import perfmark
import time
from collections.abc import Mapping
from typing import Any, Literal

import vllm.envs as envs
from vllm.config import VllmConfig
from vllm.exceptions import VLLMValidationError
from vllm.inputs import (
    EngineInput,
    PromptType,
    SingletonInput,
    split_enc_dec_input,
)
from vllm.inputs.preprocess import InputPreprocessor
from vllm.logger import init_logger
from vllm.lora.request import LoRARequest
from vllm.multimodal import MULTIMODAL_REGISTRY, MultiModalRegistry
from vllm.multimodal.encoder_budget import MultiModalBudget
from vllm.multimodal.inputs import MultiModalFeatureSpec
from vllm.multimodal.utils import argsort_mm_positions
from vllm.platforms import current_platform
from vllm.pooling_params import PoolingParams
from vllm.renderers import BaseRenderer, renderer_from_config
from vllm.sampling_params import SamplingParams
from vllm.tasks import GENERATION_TASKS, POOLING_TASKS, SupportedTask
from vllm.tokenizers import TokenizerLike
from vllm.utils import length_from_prompt_token_ids_or_embeds, random_uuid
from vllm.utils.async_utils import make_async
from vllm.utils.jsontree import json_iter_leaves
from vllm.v1.engine import EngineCoreRequest

logger = init_logger(__name__)


class InputProcessor:
    def __init__(
        self,
        vllm_config: VllmConfig,
        renderer: BaseRenderer | None = None,
        *,
        mm_registry: MultiModalRegistry = MULTIMODAL_REGISTRY,
    ) -> None:
        self.vllm_config = vllm_config
        self.model_config = model_config = vllm_config.model_config
        self.cache_config = vllm_config.cache_config
        self.lora_config = vllm_config.lora_config
        self.scheduler_config = vllm_config.scheduler_config
        self.speculative_config = vllm_config.speculative_config
        self.structured_outputs_config = vllm_config.structured_outputs_config
        self.observability_config = vllm_config.observability_config
        self.use_v2_model_runner = vllm_config.use_v2_model_runner

        self.generation_config_fields = model_config.try_get_generation_config()

        self.renderer = renderer or renderer_from_config(vllm_config)

        self.supports_mm_inputs = mm_registry.supports_multimodal_inputs(model_config)
        self.mm_encoder_cache_size = 0
        self.skip_prompt_length_check = False
        if self.supports_mm_inputs:
            mm_budget = MultiModalBudget(vllm_config, mm_registry)
            self.mm_encoder_cache_size = mm_budget.encoder_cache_size
            self.skip_prompt_length_check = (
                mm_budget.processor.info.skip_prompt_length_check
            )
            mm_budget.reset_cache()  # Not used anymore

        self.input_preprocessor = InputPreprocessor(
            vllm_config,
            renderer=renderer,
            mm_registry=mm_registry,
        )

        # Raw-prompt preprocessing (tokenization and multimodal processing)
        # is blocking, so async callers should run it on the renderer's
        # thread pool to keep their event loop responsive.
        self.process_inputs_async = make_async(
            self.process_inputs, executor=self.renderer._executor
        )

    @property
    def tokenizer(self) -> TokenizerLike | None:
        return self.renderer.tokenizer

    def get_tokenizer(self) -> TokenizerLike:
        return self.renderer.get_tokenizer()

    def _validate_params(
        self,
        params: SamplingParams | PoolingParams,
        supported_tasks: tuple[SupportedTask, ...],
    ) -> None:
        """Raise `ValueError` if SamplingParams or PoolingParams is not valid."""
        if isinstance(params, SamplingParams):
            supported_generation_tasks = [
                task for task in supported_tasks if task in GENERATION_TASKS
            ]
            if not supported_generation_tasks:
                raise VLLMValidationError("This model does not support generation")

            params.verify(
                self.model_config,
                self.speculative_config,
                self.structured_outputs_config,
                self.tokenizer,
            )

            if self.model_config.return_sampling_mask:
                if params.temperature <= 0:
                    raise ValueError(
                        "sampling distribution replay requires temperature > 0"
                    )
                if params.top_k <= 0:
                    raise ValueError(
                        "sampling distribution replay requires top_k > 0 to "
                        "bound sampling mask size, reduce transfer overhead, "
                        "and avoid potential OOMs"
                    )
            if params.thinking_token_budget is not None and (
                self.vllm_config.reasoning_config is None
                or not self.vllm_config.reasoning_config.enabled
            ):
                raise VLLMValidationError(
                    "thinking_token_budget is set but reasoning_config is "
                    "not configured. Please set --reasoning-parser "
                    "and/or --reasoning-config to use thinking_token_budget."
                )
        elif isinstance(params, PoolingParams):
            supported_pooling_tasks = [
                task for task in supported_tasks if task in POOLING_TASKS
            ]
            if not supported_pooling_tasks:
                raise VLLMValidationError("This model does not support pooling")

            if params.task is None:
                if "token_embed" in supported_pooling_tasks:
                    params.task = "token_embed"
                elif "token_classify" in supported_pooling_tasks:
                    params.task = "token_classify"
                elif "plugin" in supported_pooling_tasks:
                    params.task = "plugin"

            if params.task not in supported_pooling_tasks:
                raise VLLMValidationError(
                    f"Unsupported task: {params.task!r} "
                    f"Supported tasks: {supported_pooling_tasks}"
                )

            params.verify(self.model_config)
        else:
            raise TypeError(
                f"params must be either SamplingParams or PoolingParams, "
                f"but got {type(params).__name__}"
            )

    def _validate_lora(self, lora_request: LoRARequest | None) -> None:
        if lora_request is None:
            return

        # LoRA request passed in while LoRA is not enabled
        if not self.lora_config:
            raise VLLMValidationError(
                f"Got lora_request {lora_request} but LoRA is not enabled!"
            )

        if self.tokenizer is not None:
            logger.warning_once(
                "vLLM has deprecated support for supporting different "
                "tokenizers for different LoRAs. By default, vLLM uses base "
                "model's tokenizer. If you are using a LoRA "
                "with its own tokenizer, consider specifying `--tokenizer "
                "[lora_path]` to use the LoRA tokenizer."
            )

    def _get_mm_identifier(
        self,
        mm_hash: str,
        lora_request: LoRARequest | None,
    ) -> str:
        """
        When enable_tower_connector_lora is True, multi-modal embeddings
        vary depending on the LoRA request. Therefore, the mm_hash must be
        generated based on the LoRA request to prevent incorrect cache hits.
        """
        if (
            lora_request is None
            or self.lora_config is None
            or not self.lora_config.enable_tower_connector_lora
        ):
            return mm_hash
        return f"{lora_request.lora_name}:{mm_hash}"

    def inject_into_mm_cache(
        self,
        mm_hashes: dict[str, list[str]],
        mm_kwargs: dict[str, list],
    ) -> None:
        """Inject pre-processed mm_kwargs into the processor cache.

        Call this when mm_kwargs have already been through the HF processor
        externally (e.g. by a frontend that transfers pre-processed tensors
        to the backend).  This ensures MM cache hit rate metrics are reported
        accurately and avoids redundant processing on subsequent requests
        with the same images.

        Uses ``get_and_update_item()`` with an empty prompt_updates list,
        since token expansion has already been handled externally.
        """
        cache = self.renderer.mm_processor_cache
        if cache is None:
            return
        try:
            for modality, hashes in mm_hashes.items():
                items = mm_kwargs.get(modality, [])
                for i, mm_hash in enumerate(hashes):
                    if i < len(items) and items[i] is not None:
                        # Insert into cache via get_and_update_item.
                        # Use the returned item (may be an address for SHM
                        # cache or the original item for LRU cache).
                        items[i], _ = cache.get_and_update_item(
                            (items[i], []),
                            mm_hash,
                        )
            # Update cache stats to reflect the externally processed items
            self.renderer.update_mm_cache_stats()
        except Exception:
            logger.warning(
                "Failed to inject mm_kwargs into processor cache",
                exc_info=True,
            )

    @staticmethod
    def assign_request_id(request: EngineCoreRequest):
        """Replace the externally supplied request ID with an internal request ID
        that adds 8 random characters in order to ensure uniqueness.
        """
        if request.external_req_id is not None:
            raise ValueError(
                "The external_req_id field should not be set on EngineCoreRequests"
                " passed to vLLM; use the request_id field."
            )
        request.external_req_id = request.request_id
        if envs.VLLM_DISABLE_REQUEST_ID_RANDOMIZATION:
            logger.warning_once(
                "VLLM_DISABLE_REQUEST_ID_RANDOMIZATION is set and will be "
                "removed in a future release. Duplicate externally-provided "
                "request IDs may cause failures and/or subtle correctness errors."
            )
        else:
            request.request_id = f"{request.external_req_id}-{random_uuid():.8}"

    def process_inputs(
        self,
        request_id: str,
        prompt: PromptType | EngineInput,
        params: SamplingParams | PoolingParams,
        supported_tasks: tuple[SupportedTask, ...],
        arrival_time: float | None = None,
        lora_request: LoRARequest | None = None,
        tokenization_kwargs: dict[str, Any] | None = None,
        trace_headers: Mapping[str, str] | None = None,
        priority: int = 0,
        data_parallel_rank: int | None = None,
        resumable: bool = False,
        session_id: str | None = None,
    ) -> EngineCoreRequest:
        with perfmark.region("vllm-044"):
            self._validate_params(params, supported_tasks)
            self._validate_lora(lora_request)

            parallel_config = self.vllm_config.parallel_config
            dp_size = parallel_config.data_parallel_size
            dp_local_size = parallel_config.data_parallel_size_local
            num_ranks = dp_local_size if parallel_config.local_engines_only else dp_size
            if data_parallel_rank is not None and not (0 <= data_parallel_rank < num_ranks):
                raise VLLMValidationError(
                    f"data_parallel_rank {data_parallel_rank} "
                    f"is out of range [0, {num_ranks})."
                )

            if isinstance(prompt, dict) and "type" in prompt:
                if tokenization_kwargs:
                    logger.warning_once(
                        "Passing tokenization_kwargs to InputProcessor is deprecated "
                        "and will be removed in v0.18. You should instead pass "
                        "them to Renderer.render_cmpl() or Renderer.render_chat()."
                    )

                if arrival_time is None:
                    arrival_time = prompt.get("arrival_time", time.time())  # type: ignore[assignment]

                processed_inputs: EngineInput = prompt  # type: ignore[assignment]
            else:
                logger.warning_once(
                    "Passing raw prompts to InputProcessor is deprecated "
                    "and will be removed in v0.18. You should instead pass "
                    "the outputs of Renderer.render_cmpl() or Renderer.render_chat()."
                )

                if arrival_time is None:
                    arrival_time = time.time()

                processed_inputs = self.input_preprocessor.preprocess(
                    prompt,
                    tokenization_kwargs=tokenization_kwargs,
                )

            current_platform.validate_request(processed_inputs, params)

            encoder_inputs, decoder_inputs = split_enc_dec_input(processed_inputs)
            self._validate_model_inputs(encoder_inputs, decoder_inputs)

            # Mypy can be conservative for TypedDict unions; normalize access.
            if decoder_inputs["type"] == "embeds":
                prompt_embeds = decoder_inputs["prompt_embeds"]
                prompt_token_ids = decoder_inputs.get("prompt_token_ids")
                prompt_is_token_ids = decoder_inputs.get("is_token_ids")
            else:
                prompt_token_ids = decoder_inputs["prompt_token_ids"]
                prompt_embeds = None
                prompt_is_token_ids = None

            sampling_params = None
            pooling_params = None
            if isinstance(params, SamplingParams):
                # TODO: can we avoid cloning here in multiproc case?
                sampling_params = params.clone()
                # If unset max tokens, then generate up to the max_model_len.
                if sampling_params.max_tokens is None:
                    seq_len = length_from_prompt_token_ids_or_embeds(
                        prompt_token_ids, prompt_embeds
                    )
                    sampling_params.max_tokens = self.model_config.max_model_len - seq_len

                sampling_params.update_from_generation_config(
                    self.generation_config_fields,
                    self.renderer.get_eos_token_id(),
                )
                if self.tokenizer is not None:
                    sampling_params.update_from_tokenizer(self.tokenizer)
            else:
                pooling_params = params.clone()

            # Multimodal related.
            mm_features: list[MultiModalFeatureSpec] | None = None

            if decoder_inputs["type"] == "multimodal":
                decoder_mm_inputs = decoder_inputs["mm_kwargs"]
                decoder_mm_positions = decoder_inputs["mm_placeholders"]
                decoder_mm_hashes = decoder_inputs["mm_hashes"]

                if not all(
                    isinstance(leaf, str) for leaf in json_iter_leaves(decoder_mm_hashes)
                ):
                    raise ValueError(
                        f"mm_hashes must contain only strings, got: {decoder_mm_hashes}. "
                        "This is likely due to an incorrect custom implementation of "
                        "MultiModalProcessor.apply method."
                    )

                # Merge and flatten multimodal placeholders, hashes and inputs
                # from dictionaries to lists, and sort them by each item's position
                # in the input sequence.
                sorted_mm_idxs = argsort_mm_positions(decoder_mm_positions)

                mm_features = []
                for modality, idx in sorted_mm_idxs:
                    base_mm_hash = decoder_mm_hashes[modality][idx]
                    mm_features.append(
                        MultiModalFeatureSpec(
                            data=decoder_mm_inputs[modality][idx],
                            modality=modality,
                            identifier=self._get_mm_identifier(
                                base_mm_hash,
                                lora_request,
                            ),
                            mm_position=decoder_mm_positions[modality][idx],
                            mm_hash=base_mm_hash,
                        )
                    )

            return EngineCoreRequest(
                request_id=request_id,
                prompt_token_ids=prompt_token_ids,
                prompt_embeds=prompt_embeds,
                prompt_is_token_ids=prompt_is_token_ids,
                mm_features=mm_features,
                sampling_params=sampling_params,
                pooling_params=pooling_params,
                arrival_time=arrival_time,
                lora_request=lora_request,
                cache_salt=decoder_inputs.get("cache_salt"),
                priority=priority,
                data_parallel_rank=data_parallel_rank,
                trace_headers=trace_headers,
                resumable=resumable,
                session_id=session_id,
            )

    def _validate_prompt_len(
        self,
        prompt_len: int,
        prompt_type: Literal["encoder", "decoder"],
    ):
        if self.skip_prompt_length_check:
            return

        if prompt_len == 0 and prompt_type == "decoder":
            raise VLLMValidationError(f"The {prompt_type} prompt cannot be empty")

        model_config = self.model_config
        max_prompt_len = (
            model_config.max_model_len
            if prompt_type == "decoder"
            else self.mm_encoder_cache_size
        )
        if prompt_len > max_prompt_len:
            if self.supports_mm_inputs:
                suggestion = (
                    "Make sure that `max_model_len` is no smaller than the "
                    "number of text tokens plus multimodal tokens. For image "
                    "inputs, the number of image tokens depends on the number "
                    "of images, and possibly their aspect ratios as well."
                )
            else:
                suggestion = (
                    "Make sure that `max_model_len` is no smaller than the "
                    "number of text tokens."
                )

            raise VLLMValidationError(
                f"The {prompt_type} prompt (length {prompt_len}) is "
                f"longer than the maximum model length of {max_prompt_len}. "
                f"{suggestion}"
            )
        elif prompt_len == max_prompt_len and model_config.runner_type == "generate":
            suggestion = (
                "Make sure that `max_model_len` is no smaller than the "
                "number of text tokens (prompt + requested output tokens)."
            )
            raise VLLMValidationError(
                f"The {prompt_type} prompt (length {prompt_len}) plus the number of "
                f"requested output tokens (at least 1) is longer than the maximum "
                f"model length of {max_prompt_len}. {suggestion}"
            )

    def _validate_model_input(
        self,
        prompt_input: SingletonInput,
        prompt_type: Literal["encoder", "decoder"],
    ) -> None:
        model_config = self.model_config
        tokenizer = self.tokenizer

        prompt_ids = (
            None
            if prompt_input["type"] == "embeds"
            else prompt_input["prompt_token_ids"]
        )
        prompt_embeds = (
            prompt_input["prompt_embeds"] if prompt_input["type"] == "embeds" else None
        )

        prompt_len = length_from_prompt_token_ids_or_embeds(prompt_ids, prompt_embeds)
        self._validate_prompt_len(prompt_len, prompt_type)

        if prompt_input["type"] == "multimodal":
            decoder_mm_positions = prompt_input["mm_placeholders"]
            for modality, mm_positions in decoder_mm_positions.items():
                for mm_position in mm_positions:
                    num_embeds = mm_position.get_num_embeds()
                    if num_embeds > self.mm_encoder_cache_size:
                        raise VLLMValidationError(
                            f"The {prompt_type} prompt contains a(n) {modality} item "
                            f"with {num_embeds} embedding tokens, which exceeds the "
                            f"pre-allocated encoder cache size "
                            f"{self.mm_encoder_cache_size}. Please reduce the input "
                            f"size or increase the encoder cache size "
                            f"by setting --limit-mm-per-prompt at startup."
                        )

        if prompt_ids and tokenizer is not None:
            max_input_id = max(prompt_ids, default=0)
            min_input_id = min(prompt_ids, default=0)

            # NOTE: tokenizer.max_token_id is the tokenizer’s vocab size while
            # self.model_config.get_vocab_size() is the model’s vocab size.
            # For Qwen3 models, the language model has extra tokens that do
            # not exist in the tokenizer, and vice versa for multimodal
            # placeholder tokens in some multimodal models.
            # See https://github.com/QwenLM/Qwen3/issues/29#issuecomment-1933720399 # noqa: E501
            # and https://github.com/vllm-project/vllm/pull/22471#discussion_r2312251421 # noqa: E501

            # Here we take the max of the two to determine if a token id is
            # truly out-of-vocabulary.
            model_vocab_size = model_config.get_vocab_size()
            # A negative id is out of vocabulary just like an over-large one,
            # but is not caught by the upper-bound check below. Reject it here
            # so it is not used as an embedding index downstream. This
            # validation path is shared by generate, embedding and pooling
            # requests, so the check covers all three.
            if min_input_id < 0:
                raise VLLMValidationError(
                    f"Token id {min_input_id} is out of vocabulary"
                )
            if max_input_id > max(tokenizer.max_token_id, model_vocab_size - 1):
                raise VLLMValidationError(
                    f"Token id {max_input_id} is out of vocabulary"
                )

    def _validate_model_inputs(
        self,
        encoder_input: SingletonInput | None,
        decoder_input: SingletonInput,
    ):
        if encoder_input is not None:
            self._validate_model_input(encoder_input, prompt_type="encoder")

        self._validate_model_input(decoder_input, prompt_type="decoder")

--- FILE: tests/test_case.py ---
"""Bounded correctness and reachability test for vllm-044."""
from driver import run

TARGET = "vllm-044"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)

--- FILE: tests/driver.py ---
"""Bounded native vLLM correctness and marker-reachability scenarios.

Each scenario intentionally combines easy and hard inputs and changes several
independent dimensions. Twelve direct calls (or eight model batches) give a
selector enough observations to discover useful raw or derived state without
turning this correctness workload into a throughput benchmark.
"""
import argparse
import os
import sys
from pathlib import Path


DIRECT_STATE_COUNT = 12
MODEL_BATCH_SIZES = (1, 2, 3, 4, 5, 6, 7, 8)


def _args():
    p = argparse.ArgumentParser()
    p.add_argument("--source-root", required=True)
    return p.parse_args()


def _request(i, priority=0, arrival=None, prompt_tokens=3, max_tokens=1):
    from vllm import SamplingParams
    from vllm.v1.request import Request

    # Token ids stay inside OPT-125m's vocabulary while prompt length changes.
    token_ids = [2 + ((i + offset) % 100) for offset in range(prompt_tokens)]
    return Request(
        str(i),
        token_ids,
        SamplingParams(max_tokens=max_tokens),
        None,
        priority=priority,
        arrival_time=float(i if arrival is None else arrival),
    )


def _filled_queue(cls, size, seed=0, common_priority=None):
    q = cls()
    requests = []
    for offset in range(size):
        priority = common_priority if common_priority is not None else size - offset
        request = _request(
            seed + offset,
            priority=priority,
            arrival=seed + offset / 10,
            prompt_tokens=1 + (offset % 7),
            max_tokens=1 + (offset % 4),
        )
        q.add_request(request)
        requests.append(request)
    return q, requests


def _queue_scenario(case_id):
    from vllm.v1.core.sched.request_queue import FCFSRequestQueue, PriorityRequestQueue

    number = int(case_id[-3:])
    cls = FCFSRequestQueue if number < 20 else PriorityRequestQueue

    if number in (14, 20):
        # add_request observes queue depths 0..11.
        q = cls()
        for i in range(DIRECT_STATE_COUNT):
            q.add_request(_request(i, priority=DIRECT_STATE_COUNT - i,
                                   prompt_tokens=i + 1,
                                   max_tokens=1 + (i % 4)))
        assert len(q) == DIRECT_STATE_COUNT
    elif number in (15, 21):
        # peek_request observes twelve distinct front priorities and sizes.
        for size in range(1, DIRECT_STATE_COUNT + 1):
            q, requests = _filled_queue(cls, size, seed=100 * size,
                                        common_priority=size)
            assert q.peek_request() in requests and len(q) == size
            assert q.peek_request().priority == size
    elif number in (16, 22):
        # pop_request observes queue sizes 1..12 at entry.
        for size in range(1, DIRECT_STATE_COUNT + 1):
            q, requests = _filled_queue(cls, size, seed=200 * size)
            popped = q.pop_request()
            assert popped in requests and len(q) == size - 1
    elif number in (17, 23):
        # prepend_request sees distinct priorities, arrivals, and prompt sizes.
        for i in range(DIRECT_STATE_COUNT):
            q, _ = _filled_queue(cls, 1 + (i % 4), seed=300 + 10 * i)
            incoming = _request(400 + i, priority=i, arrival=-i,
                                prompt_tokens=i + 1,
                                max_tokens=1 + (i % 5))
            q.prepend_request(incoming)
            assert incoming in q
    elif number in (18, 24):
        # prepend_requests sees incoming counts 0..11.
        for incoming_count in range(DIRECT_STATE_COUNT):
            q, original = _filled_queue(cls, 1 + (incoming_count % 3),
                                         seed=500 + 20 * incoming_count)
            other, incoming = _filled_queue(cls, incoming_count,
                                             seed=1000 + 20 * incoming_count)
            q.prepend_requests(other)
            assert len(q) == len(original) + incoming_count
            assert set(q) == set(original + incoming)
    else:
        # remove_request sees distinct request priorities and queue sizes.
        for i in range(DIRECT_STATE_COUNT):
            q, requests = _filled_queue(cls, 2 + i, seed=2000 + 20 * i)
            removed = requests[i % len(requests)]
            q.remove_request(removed)
            assert len(q) == 1 + i and removed not in q


def _request_scenario():
    from vllm import SamplingParams
    from vllm.v1.request import Request

    for i in range(DIRECT_STATE_COUNT):
        prompt_length = i + 1
        limit = 1 + (i % 6)
        prompt = [2 + ((i + offset) % 100) for offset in range(prompt_length)]
        request = Request(
            f"request-{i}",
            prompt,
            SamplingParams(max_tokens=limit),
            None,
            priority=i,
            arrival_time=i / 10,
        )
        assert request.request_id == f"request-{i}"
        assert request.max_tokens == limit
        assert request.num_prompt_tokens == prompt_length


def _penalty_scenario(case_id):
    import torch
    from vllm.v1.sample.ops.penalties import _convert_to_tensors, apply_all_penalties

    if case_id == "vllm-050":
        for batch_size in range(1, DIRECT_STATE_COUNT + 1):
            rows = [list(range((batch_size + row) % 6))
                    for row in range(batch_size)]
            output = _convert_to_tensors(rows, 32, torch.device("cpu"))
            expected_width = max(map(len, rows), default=0)
            assert tuple(output.shape) == (batch_size, expected_width)
    else:
        for batch_size in range(1, DIRECT_STATE_COUNT + 1):
            vocab_size = 16 + batch_size
            rows = [list(range((batch_size + row) % 5))
                    for row in range(batch_size)]
            logits = torch.linspace(-1.0, 1.0, batch_size * vocab_size).reshape(
                batch_size, vocab_size
            )
            prompt = torch.tensor(
                [[(row + col) % vocab_size for col in range(1 + batch_size % 5)]
                 for row in range(batch_size)]
            )
            scale = batch_size / 100
            presence = torch.full((batch_size,), scale)
            frequency = torch.linspace(-scale, scale, batch_size)
            repetition = torch.full((batch_size,), 1.0 + scale)
            output = apply_all_penalties(
                logits, prompt, presence, frequency, repetition, rows
            )
            assert output.shape == logits.shape and torch.isfinite(output).all()


def _topk_topp_scenario():
    import torch
    from vllm.v1.sample.ops.topk_topp_sampler import TopKTopPSampler

    sampler = TopKTopPSampler()
    vocab_size = 16
    for batch_size in range(1, DIRECT_STATE_COUNT + 1):
        logits = torch.arange(batch_size * vocab_size, dtype=torch.float32).reshape(
            batch_size, vocab_size
        )
        top_k = 1 + (batch_size - 1) % vocab_size
        k = torch.full((batch_size,), top_k)
        p = torch.full((batch_size,), 0.50 + batch_size / 25)
        sampled, returned = sampler.forward_cpu(logits, {}, k, p)
        assert tuple(sampled.shape) == (batch_size,) and returned is None
        assert bool(((sampled >= 0) & (sampled < vocab_size)).all())


def _remove_all_scenario():
    from vllm.v1.core.sched.utils import remove_all

    for removal_count in range(DIRECT_STATE_COUNT):
        values = list(range(DIRECT_STATE_COUNT + 3))
        to_remove = set(range(removal_count))
        expected = [value for value in values if value not in to_remove]
        result = remove_all(values, to_remove)
        assert result == expected


def _block_pool_scenario():
    from vllm import SamplingParams
    from vllm.utils.hashing import sha256
    from vllm.v1.core.block_pool import BlockPool
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash
    from vllm.v1.request import Request

    init_none_hash(sha256)
    for new_block_count in range(1, DIRECT_STATE_COUNT + 1):
        block_size = 1 + new_block_count
        token_ids = list(range(new_block_count * block_size))
        sampling_params = SamplingParams(max_tokens=1 + new_block_count % 4)
        sampling_params.update_from_generation_config({}, eos_token_id=100)
        request = Request(
            request_id=f"cache-{new_block_count}",
            prompt_token_ids=token_ids,
            sampling_params=sampling_params,
            pooling_params=None,
            block_hasher=get_request_block_hasher(block_size, sha256),
        )
        pool = BlockPool(
            num_gpu_blocks=new_block_count + 1,
            enable_caching=True,
            hash_block_size=block_size,
        )
        blocks = pool.get_new_blocks(new_block_count)
        pool.cache_full_blocks(
            request=request,
            blocks=blocks,
            num_cached_blocks=0,
            num_full_blocks=new_block_count,
            block_size=block_size,
            kv_cache_group_id=new_block_count % 3,
        )
        assert len(pool.cached_block_hash_to_block) == new_block_count
        assert all(block.block_hash is not None for block in blocks)


def _detokenizer_scenario():
    from vllm import SamplingParams
    from vllm.v1.engine import EngineCoreRequest
    from vllm.v1.engine.detokenizer import BaseIncrementalDetokenizer

    class SimpleDetokenizer(BaseIncrementalDetokenizer):
        def decode_next(self, next_token_id):
            return chr(ord("a") + next_token_id % 26)

    for new_token_count in range(DIRECT_STATE_COUNT):
        params = SamplingParams(
            max_tokens=DIRECT_STATE_COUNT,
            stop="zz",
            include_stop_str_in_output=bool(new_token_count % 2),
        )
        request = EngineCoreRequest(
            request_id=f"detokenize-{new_token_count}",
            prompt_token_ids=[1, 2, 3],
            mm_features=None,
            sampling_params=params,
            pooling_params=None,
            arrival_time=float(new_token_count),
            lora_request=None,
            cache_salt=None,
            data_parallel_rank=None,
        )
        detokenizer = SimpleDetokenizer(request)
        token_ids = list(range(new_token_count))
        stop_terminated = bool(new_token_count % 3 == 0)
        matched = detokenizer.update(token_ids, stop_terminated)
        assert matched is None
        assert detokenizer.num_output_tokens() == new_token_count


def _request_output_scenario():
    from vllm import SamplingParams
    from vllm.v1.engine import EngineCoreRequest, FinishReason
    from vllm.v1.engine.output_processor import RequestState

    for new_token_count in range(1, DIRECT_STATE_COUNT + 1):
        params = SamplingParams(max_tokens=DIRECT_STATE_COUNT, detokenize=False)
        request = EngineCoreRequest(
            request_id=f"output-{new_token_count}",
            external_req_id=f"external-{new_token_count}",
            prompt_token_ids=[1, 2, 3],
            mm_features=None,
            sampling_params=params,
            pooling_params=None,
            arrival_time=float(new_token_count),
            lora_request=None,
            cache_salt=None,
            data_parallel_rank=None,
        )
        state = RequestState.from_new_request(
            tokenizer=None,
            request=request,
            prompt="prompt",
            parent_req=None,
            request_index=0,
            queue=None,
            log_stats=False,
            stream_interval=1,
        )
        token_ids = list(range(new_token_count))
        assert state.detokenizer is not None
        state.detokenizer.update(token_ids, stop_terminated=False)
        finish_reason = FinishReason.LENGTH if new_token_count % 3 == 0 else None
        output = state.make_request_output(
            new_token_ids=token_ids,
            pooling_output=None,
            finish_reason=finish_reason,
            stop_reason=None,
        )
        assert output is not None
        assert output.finished == (finish_reason is not None)


def _sampling_params(index, output_tokens):
    from vllm import SamplingParams

    sampled = index % 3 == 2
    penalized = index >= 4
    return SamplingParams(
        max_tokens=output_tokens,
        min_tokens=1,
        temperature=0.75 if sampled else 0.0,
        top_k=5 + index if sampled else 0,
        top_p=0.72 + index / 100 if sampled else 1.0,
        presence_penalty=index / 20 if penalized else 0.0,
        frequency_penalty=-(index / 25) if penalized else 0.0,
        repetition_penalty=1.0 + index / 50 if penalized else 1.0,
        seed=1000 + index,
    )


def _llm_scenario(case_id):
    os.environ.setdefault("VLLM_TARGET_DEVICE", "cpu")
    os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from vllm import LLM

    kwargs = dict(
        model="facebook/opt-125m",
        enforce_eager=True,
        max_model_len=96,
        max_num_seqs=max(MODEL_BATCH_SIZES),
        gpu_memory_utilization=0.05,
        enable_prefix_caching=True,
        scheduling_policy="priority",
    )
    if case_id in {"vllm-053", "vllm-056", "vllm-057"}:
        kwargs["speculative_config"] = {
            "method": "ngram",
            "num_speculative_tokens": 2,
            "prompt_lookup_min": 2,
            "prompt_lookup_max": 4,
        }
    llm = LLM(**kwargs)

    easy = ("One.", "Two short words.", "A small ordinary request.")
    shared = "alpha beta gamma delta epsilon zeta eta theta " * 3
    medium = "Explain one practical use of a queue in two words."

    for batch_index, batch_size in enumerate(MODEL_BATCH_SIZES):
        prompts = []
        params = []
        priorities = []
        for row in range(batch_size):
            if batch_index <= 1:
                text = easy[row % len(easy)] + f" Batch {batch_index}, item {row}."
            elif batch_index <= 3:
                text = medium + f" Distinguish item {row} with value {row * row}."
            else:
                # Long common prefixes generate both cache hits and misses. The
                # final batch perturbs half the prefix to exercise the miss path.
                prefix = shared if not (batch_index == 7 and row % 2) else "omega " + shared
                text = prefix + f" unique suffix {batch_index}-{row}"
            # Structured text prompts exercise the dictionary input branch.
            prompts.append({"prompt": text} if batch_index in (3, 6) else text)
            params.append(_sampling_params(batch_index + row,
                                           1 + ((batch_index + row) % 4)))
            priorities.append((batch_size - row) % 5)

        tokenization_options = [
            ("add_special_tokens", batch_index % 2 == 0),
            ("do_lower_case", False),
            ("needs_detokenization", True),
            ("truncation_side", "left"),
            ("truncate_prompt_tokens", 90),
            ("max_length", 90),
            ("padding", False),
        ]
        tokenization_kwargs = dict(tokenization_options[:batch_index]) or None
        outputs = llm.generate(
            prompts,
            params,
            # Integers are valid bool-like values here and expose levels 0..7.
            use_tqdm=batch_index,
            priority=priorities,
            tokenization_kwargs=tokenization_kwargs,
        )
        assert len(outputs) == batch_size
        for output, param in zip(outputs, params):
            assert output.outputs
            generated = len(output.outputs[0].token_ids)
            assert 1 <= generated <= param.max_tokens


def run(case_id):
    args = _args()
    sys.path.insert(0, args.source_root)
    from marker_probe import Probe

    probe = Probe()
    import vllm

    source_root = Path(args.source_root).resolve()
    loaded_root = Path(vllm.__file__).resolve()
    assert loaded_root.is_relative_to(source_root), (
        f"vllm imported from {loaded_root}, outside requested source root {source_root}"
    )
    if case_id == "vllm-005":
        _block_pool_scenario()
    elif case_id == "vllm-043":
        _detokenizer_scenario()
    elif case_id == "vllm-048":
        _request_output_scenario()
    elif 14 <= int(case_id[-3:]) <= 25:
        _queue_scenario(case_id)
    elif case_id == "vllm-039":
        _remove_all_scenario()
    elif case_id == "vllm-049":
        _request_scenario()
    elif case_id in {"vllm-050", "vllm-051"}:
        _penalty_scenario(case_id)
    elif case_id == "vllm-052":
        _topk_topp_scenario()
    else:
        _llm_scenario(case_id)
    probe.finish(case_id)

--- FILE: tests/marker_probe.py ---
"""Native correctness-test marker observer; does not count instructions."""
import contextlib
import json
import os
import sys
import types
from collections import Counter


class Probe:
    def __init__(self):
        self.hits=Counter()
        self.instrumented=bool(os.environ.get('DRPERF'))
        original=None
        if self.instrumented:
            import perfmark
            original=perfmark.region
        module=types.ModuleType('perfmark')
        @contextlib.contextmanager
        def region(name, **pcvs):
            self.hits[name]+=1
            if original is None:
                yield
            else:
                with original(name, **pcvs):
                    yield
        module.region=region
        # Only instrumentation is replaced. Target functions and their
        # dependencies run normally; this is a reachability/correctness test.
        sys.modules['perfmark']=module

    def finish(self, target):
        print(json.dumps({'marker_hits':dict(self.hits),'target':target,
                          'measurement':'drperf' if self.instrumented else 'native correctness and reachability only'},sort_keys=True))
        assert self.hits[target]>0, f'test passed its value assertions but did not reach marker {target}'

--- FILE: TASK.md ---
# InputProcessor.process_inputs

Inspect the marked function in `vllm/v1/engine/input_processor.py` at the pinned revision.
The marker has no PCVs; identify useful state expressions for its cost.

Exercise the named vLLM CPU execution path with a small cached model and bounded request batches. Adjust request options to reach this method; no particular dependency is supplied.

Apply this case patch independently in an upstream checkout. The snapshot is
source context, not a standalone program. Install the matching project
dependencies, make `perfmark/python` importable and build libperfmark before
measuring. See `case.json` for the test command and recorded validation status.
Keep the code behavior unchanged while adding observation state.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.

--- FILE: case.json ---
{
  "schema_version": 1,
  "id": "vllm-044",
  "title": "InputProcessor.process_inputs body",
  "language": "python",
  "region": {
    "symbol": "InputProcessor.process_inputs",
    "start_line": 270,
    "end_line": 400,
    "kind": "function"
  },
  "marker": {
    "kind": "python-context",
    "name": "vllm-044",
    "pcvs": []
  },
  "status": "collected",
  "build_status": "not-built",
  "workload": {
    "description": "Exercise the named vLLM CPU execution path with a small cached model and bounded request batches. Adjust request options to reach this method; no particular dependency is supplied.",
    "command": [
      "{python}",
      "tests/test_case.py",
      "--source-root",
      "{source_root}"
    ]
  },
  "source": {
    "repository": "https://github.com/vllm-project/vllm",
    "revision": "2cf0a6915ce544dc493a0990f2ea38d81601128a",
    "path": "vllm/v1/engine/input_processor.py",
    "sha256": "f9a7946a16acc2374ff2bdfc22f212cb43461d9ef4d99c5e19a536339f11212f"
  },
  "tests": {
    "files": [
      "tests/test_case.py",
      "tests/driver.py",
      "tests/marker_probe.py"
    ],
    "command": [
      "{python}",
      "tests/test_case.py",
      "--source-root",
      "{source_root}"
    ],
    "validation": {
      "status": "not-run",
      "details": "Concrete bounded scenario is provided, but this target was not run with its individual patch; target-specific marker reachability remains unverified."
    },
    "coverage_note": "Runs a concrete cached-model CPU workload with varied prompts, token limits, and a repeated prefix. It may reach the target, but vLLM configuration and fast-path choices can bypass the marked block; Probe.finish requires observed marker entry."
  }
}
