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

CASE: vllm-002
SANITIZED BENCHMARK:
--- FILE: vllm/entrypoints/offline_utils.py ---
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project

import perfmark
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from tqdm import tqdm
from typing_extensions import TypeVar

from vllm import (
    PoolingParams,
    PoolingRequestOutput,
    PromptType,
    RequestOutput,
    SamplingParams,
)
from vllm.config import ModelConfig
from vllm.entrypoints.chat_utils import (
    ChatCompletionMessageParam,
    ChatTemplateContentFormatOption,
)
from vllm.inputs import EngineInput
from vllm.logger import init_logger
from vllm.lora.request import LoRARequest
from vllm.renderers import BaseRenderer, ChatParams, merge_kwargs
from vllm.renderers.inputs.preprocess import (
    conversation_to_seq,
    parse_model_prompt,
    prompt_to_seq,
)
from vllm.sampling_params import RequestOutputKind
from vllm.utils.counter import Counter
from vllm.utils.mistral import is_mistral_tokenizer
from vllm.utils.tqdm_utils import maybe_tqdm
from vllm.v1.engine.llm_engine import LLMEngine

logger = init_logger(__name__)


_P = TypeVar("_P", bound=SamplingParams | PoolingParams | None)
_O = TypeVar(
    "_O",
    bound=RequestOutput | PoolingRequestOutput,
    default=RequestOutput | PoolingRequestOutput,
)
_R = TypeVar("_R", default=Any)


class OfflineInferenceMixin:
    """Offline inference utils"""

    request_counter: Counter
    renderer: BaseRenderer
    llm_engine: "LLMEngine"
    model_config: ModelConfig

    def _resolve_mm_lora(
        self,
        prompt: EngineInput,
        lora_request: LoRARequest | None,
    ) -> LoRARequest | None:
        if prompt["type"] != "multimodal":
            return lora_request

        lora_config = self.llm_engine.vllm_config.lora_config
        default_mm_loras = None if lora_config is None else lora_config.default_mm_loras
        if not default_mm_loras:
            return lora_request

        prompt_modalities = prompt["mm_placeholders"].keys()
        intersection = set(prompt_modalities).intersection(default_mm_loras.keys())
        if not intersection:
            return lora_request

        if len(intersection) > 1:
            # TODO: Would be nice to be able to have multiple loras per prompt
            logger.warning(
                "Multiple modality specific loras were registered and would be "
                "used by a single prompt consuming several modalities; "
                "currently we only support one lora per request; as such, "
                "lora(s) registered with modalities: %s will be skipped",
                intersection,
            )
            return lora_request

        # Build the LoRA request; the ID of the default mm lora is the
        # index of the modality name sorted alphabetically + 1.
        modality_name = intersection.pop()
        modality_lora_path = default_mm_loras[modality_name]
        modality_lora_id = sorted(default_mm_loras).index(modality_name) + 1

        # If we have a collision, warn if there is a collision,
        # but always send the explicitly provided request.
        if lora_request:
            if lora_request.lora_int_id != modality_lora_id:
                logger.warning(
                    "A modality with a registered lora and a lora_request "
                    "with a different ID were provided; falling back to the "
                    "lora_request as we only apply one LoRARequest per prompt"
                )
            return lora_request

        return LoRARequest(
            modality_name,
            modality_lora_id,
            modality_lora_path,
        )

    def _preprocess_cmpl(
        self,
        prompts: Sequence[PromptType],
        tokenization_kwargs: dict[str, Any] | None = None,
        mm_processor_kwargs: dict[str, Any] | None = None,
    ) -> Sequence[EngineInput]:
        """
        Convert prompt inputs from LLM APIs (other than [LLM.chat][]) into
        a format that can be passed to `_add_request`.

        Refer to [LLM.generate][] for a complete description of the arguments.

        Returns:
            A list of `EngineInput` objects ready to be passed into LLMEngine.
        """
        renderer = self.renderer
        model_config = self.model_config

        parsed_prompts = [
            parse_model_prompt(model_config, prompt) for prompt in prompts
        ]
        tok_params = renderer.default_cmpl_tok_params.with_kwargs(
            **(tokenization_kwargs or {})
        )
        prompt_extras = (
            None
            if mm_processor_kwargs is None
            else {"mm_processor_kwargs": mm_processor_kwargs}
        )

        return renderer.render_cmpl(
            parsed_prompts,
            tok_params,
            prompt_extras=prompt_extras,
        )

    def _preprocess_cmpl_one(
        self,
        prompt: PromptType,
        tokenization_kwargs: dict[str, Any] | None = None,
        mm_processor_kwargs: dict[str, Any] | None = None,
    ) -> EngineInput:
        (engine_input,) = self._preprocess_cmpl(
            [prompt],
            tokenization_kwargs,
            mm_processor_kwargs=mm_processor_kwargs,
        )
        return engine_input

    def _preprocess_chat(
        self,
        conversations: Sequence[list[ChatCompletionMessageParam]],
        chat_template: str | None = None,
        chat_template_content_format: ChatTemplateContentFormatOption = "auto",
        chat_template_kwargs: dict[str, Any] | None = None,
        add_generation_prompt: bool = True,
        continue_final_message: bool = False,
        tools: list[dict[str, Any]] | None = None,
        tokenization_kwargs: dict[str, Any] | None = None,
        mm_processor_kwargs: dict[str, Any] | None = None,
    ) -> Sequence[EngineInput]:
        """
        Convert a list of conversations into prompts so that they can then
        be used as input for other LLM APIs.

        Refer to [LLM.chat][] for a complete description of the arguments.

        Returns:
            A list of `EngineInput` objects ready to be passed into LLMEngine.
        """
        renderer = self.renderer

        chat_params = ChatParams(
            chat_template=chat_template,
            chat_template_content_format=chat_template_content_format,
            chat_template_kwargs=merge_kwargs(
                chat_template_kwargs,
                dict(
                    add_generation_prompt=add_generation_prompt,
                    continue_final_message=continue_final_message,
                    tools=tools,
                    tokenize=(
                        is_mistral_tokenizer(renderer.tokenizer)
                        or self.model_config.enable_prompt_embeds
                    ),
                ),
            ),
            mm_processor_kwargs=mm_processor_kwargs,
        )
        tok_params = renderer.default_chat_tok_params.with_kwargs(
            **(tokenization_kwargs or {})
        )
        prompt_extras = (
            None
            if mm_processor_kwargs is None
            else {"mm_processor_kwargs": mm_processor_kwargs}
        )

        _, engine_inputs = renderer.render_chat(
            conversations,
            chat_params,
            tok_params,
            prompt_extras=prompt_extras,
        )

        return engine_inputs

    def _preprocess_chat_one(
        self,
        conversation: list[ChatCompletionMessageParam],
        chat_template: str | None = None,
        chat_template_content_format: ChatTemplateContentFormatOption = "auto",
        chat_template_kwargs: dict[str, Any] | None = None,
        add_generation_prompt: bool = True,
        continue_final_message: bool = False,
        tools: list[dict[str, Any]] | None = None,
        tokenization_kwargs: dict[str, Any] | None = None,
        mm_processor_kwargs: dict[str, Any] | None = None,
    ) -> EngineInput:
        (engine_input,) = self._preprocess_chat(
            [conversation],
            chat_template=chat_template,
            chat_template_content_format=chat_template_content_format,
            chat_template_kwargs=chat_template_kwargs,
            add_generation_prompt=add_generation_prompt,
            continue_final_message=continue_final_message,
            tools=tools,
            tokenization_kwargs=tokenization_kwargs,
            mm_processor_kwargs=mm_processor_kwargs,
        )

        return engine_input

    def _params_to_seq(
        self,
        params: _P | Sequence[_P],
        num_requests: int,
    ) -> Sequence[_P]:
        if isinstance(params, Sequence):
            if len(params) != num_requests:
                raise ValueError(
                    f"The lengths of prompts ({num_requests}) "
                    f"and params ({len(params)}) must be the same."
                )

            return params

        return [params] * num_requests

    def _lora_request_to_seq(
        self,
        lora_request: LoRARequest | None | Sequence[LoRARequest | None],
        num_requests: int,
    ) -> Sequence[LoRARequest | None]:
        if isinstance(lora_request, Sequence):
            if len(lora_request) != num_requests:
                raise ValueError(
                    f"The lengths of prompts ({num_requests}) "
                    f"and lora_request ({len(lora_request)}) must be the same."
                )

            return lora_request

        return [lora_request] * num_requests

    def _priority_to_seq(
        self,
        priority: list[int] | None,
        num_requests: int,
    ) -> Sequence[int]:
        if priority is not None:
            if len(priority) != num_requests:
                raise ValueError(
                    f"The lengths of prompts ({num_requests}) "
                    f"and priority ({len(priority)}) must be the same."
                )

            return priority

        return [0] * num_requests

    def _add_completion_requests(
        self,
        prompts: PromptType | Sequence[PromptType],
        params: SamplingParams
        | PoolingParams
        | Sequence[SamplingParams | PoolingParams],
        *,
        use_tqdm: bool | Callable[..., tqdm] = True,
        lora_request: Sequence[LoRARequest] | LoRARequest | None = None,
        priority: list[int] | None = None,
        tokenization_kwargs: dict[str, Any] | None = None,
        mm_processor_kwargs: dict[str, Any] | None = None,
    ) -> list[str]:
        seq_prompts = prompt_to_seq(prompts)
        seq_params = self._params_to_seq(params, len(seq_prompts))
        seq_lora_requests = self._lora_request_to_seq(lora_request, len(seq_prompts))
        seq_priority = self._priority_to_seq(priority, len(seq_prompts))

        return self._render_and_add_requests(
            prompts=(
                self._preprocess_cmpl_one(
                    prompt,
                    tokenization_kwargs,
                    mm_processor_kwargs=mm_processor_kwargs,
                )
                for prompt in maybe_tqdm(
                    seq_prompts,
                    use_tqdm=use_tqdm,
                    desc="Rendering prompts",
                )
            ),
            params=seq_params,
            lora_requests=seq_lora_requests,
            priorities=seq_priority,
        )

    def _run_completion(
        self,
        prompts: PromptType | Sequence[PromptType],
        params: SamplingParams
        | PoolingParams
        | Sequence[SamplingParams | PoolingParams],
        output_type: type[_O],
        *,
        use_tqdm: bool | Callable[..., tqdm] = True,
        lora_request: Sequence[LoRARequest] | LoRARequest | None = None,
        priority: list[int] | None = None,
        tokenization_kwargs: dict[str, Any] | None = None,
        mm_processor_kwargs: dict[str, Any] | None = None,
    ):
        self._add_completion_requests(
            prompts=prompts,
            params=params,
            use_tqdm=use_tqdm,
            lora_request=lora_request,
            priority=priority,
            tokenization_kwargs=tokenization_kwargs,
            mm_processor_kwargs=mm_processor_kwargs,
        )
        return self._run_engine(use_tqdm=use_tqdm, output_type=output_type)

    def _run_chat(
        self,
        messages: list[ChatCompletionMessageParam]
        | Sequence[list[ChatCompletionMessageParam]],
        params: SamplingParams
        | PoolingParams
        | Sequence[SamplingParams | PoolingParams],
        output_type: type[_O],
        *,
        use_tqdm: bool | Callable[..., tqdm] = True,
        lora_request: Sequence[LoRARequest] | LoRARequest | None = None,
        chat_template: str | None = None,
        chat_template_content_format: ChatTemplateContentFormatOption = "auto",
        add_generation_prompt: bool = True,
        continue_final_message: bool = False,
        tools: list[dict[str, Any]] | None = None,
        chat_template_kwargs: dict[str, Any] | None = None,
        tokenization_kwargs: dict[str, Any] | None = None,
        mm_processor_kwargs: dict[str, Any] | None = None,
    ):
        self._add_chat_requests(
            messages=messages,
            params=params,
            use_tqdm=use_tqdm,
            lora_request=lora_request,
            chat_template=chat_template,
            chat_template_content_format=chat_template_content_format,
            chat_template_kwargs=chat_template_kwargs,
            add_generation_prompt=add_generation_prompt,
            continue_final_message=continue_final_message,
            tools=tools,
            tokenization_kwargs=tokenization_kwargs,
            mm_processor_kwargs=mm_processor_kwargs,
        )
        return self._run_engine(output_type=output_type, use_tqdm=use_tqdm)

    def _add_chat_requests(
        self,
        messages: list[ChatCompletionMessageParam]
        | Sequence[list[ChatCompletionMessageParam]],
        params: SamplingParams
        | PoolingParams
        | Sequence[SamplingParams | PoolingParams],
        *,
        use_tqdm: bool | Callable[..., tqdm] = True,
        lora_request: Sequence[LoRARequest] | LoRARequest | None = None,
        priority: list[int] | None = None,
        chat_template: str | None = None,
        chat_template_content_format: ChatTemplateContentFormatOption = "auto",
        add_generation_prompt: bool = True,
        continue_final_message: bool = False,
        tools: list[dict[str, Any]] | None = None,
        chat_template_kwargs: dict[str, Any] | None = None,
        tokenization_kwargs: dict[str, Any] | None = None,
        mm_processor_kwargs: dict[str, Any] | None = None,
    ) -> list[str]:
        seq_convs = conversation_to_seq(messages)
        seq_params = self._params_to_seq(params, len(seq_convs))
        seq_lora_requests = self._lora_request_to_seq(lora_request, len(seq_convs))
        seq_priority = self._priority_to_seq(priority, len(seq_convs))

        # When thinking is enabled or tools are provided, and the model
        # uses special tokens for structured output (e.g. Gemma4's
        # <|channel>, <|tool_call>, <|"|>), automatically set
        # skip_special_tokens=False so these tokens are preserved in
        # output.text for downstream parsing.
        needs_parsing = (
            chat_template_kwargs and chat_template_kwargs.get("enable_thinking")
        ) or tools
        if needs_parsing:
            self._adjust_params_for_parsing(seq_params)

        return self._render_and_add_requests(
            prompts=(
                self._preprocess_chat_one(
                    conversation,
                    chat_template=chat_template,
                    chat_template_content_format=chat_template_content_format,
                    chat_template_kwargs=chat_template_kwargs,
                    add_generation_prompt=add_generation_prompt,
                    continue_final_message=continue_final_message,
                    tools=tools,
                    tokenization_kwargs=tokenization_kwargs,
                    mm_processor_kwargs=mm_processor_kwargs,
                )
                for conversation in maybe_tqdm(
                    seq_convs,
                    use_tqdm=use_tqdm,
                    desc="Rendering conversations",
                )
            ),
            params=seq_params,
            lora_requests=seq_lora_requests,
            priorities=seq_priority,
        )

    def _adjust_params_for_parsing(
        self, params: Sequence[SamplingParams | PoolingParams]
    ) -> None:
        """Set ``skip_special_tokens=False`` when the model encodes
        structured output syntax as special tokens.

        Models like Gemma4 register thinking delimiters
        (``<|channel>``/``<channel|>``) and tool call tokens
        (``<|tool_call>``/``<tool_call|>``/``<|"|>``) as special tokens.
        The default ``skip_special_tokens=True`` strips them from
        ``output.text``, breaking parsing of both reasoning blocks and
        tool calls.

        This is a no-op for models whose structured tokens are regular
        text tokens (e.g. DeepSeek's ``<think>``/``</think>``).
        """
        # The offline API currently lacks a unified rendering pipeline.
        # Until the planned Renderer refactor is complete, we hardcode
        # this token preservation logic specifically for Gemma4 models
        # to avoid regressions on other models.
        hf_config = getattr(self.model_config, "hf_config", None)
        architectures = getattr(hf_config, "architectures", [])

        if any("Gemma4" in arch for arch in architectures):
            tokenizer = self.renderer.get_tokenizer()
            vocab = tokenizer.get_vocab()
            special_ids = set(getattr(tokenizer, "all_special_ids", []))

            # Tokens used for thinking delimiters and tool call syntax
            # that some models (Gemma4) register as special tokens.
            structured_tokens = (
                "<|channel>",
                "<channel|>",  # thinking delimiters
                "<|tool_call>",
                "<tool_call|>",  # tool call delimiters
                '<|"|>',  # string quoting in tool args
            )
            needs_special = any(
                vocab.get(tok) in special_ids
                for tok in structured_tokens
                if tok in vocab
            )
            if needs_special:
                for sp in params:
                    if isinstance(sp, SamplingParams) and sp.skip_special_tokens:
                        sp.skip_special_tokens = False

    def _render_and_run_requests(
        self,
        prompts: Iterable[EngineInput],
        params: Sequence[SamplingParams | PoolingParams],
        output_type: type[_O],
        *,
        lora_requests: Sequence[LoRARequest | None] | None = None,
        priorities: Sequence[int] | None = None,
        use_tqdm: bool | Callable[..., tqdm] = True,
    ):
        if isinstance(prompts, (list, tuple)):
            logger.warning_once(
                "Rendering all prompts before adding them to the engine "
                "is less efficient than performing both on the same prompt "
                "before processing the next prompt. You should instead pass "
                "a generator that renders one prompt per iteration, as that allows "
                "engine execution to begin for the first prompt while processing "
                "the next prompt."
            )

        self._render_and_add_requests(
            prompts=prompts,
            params=params,
            lora_requests=lora_requests,
            priorities=priorities,
        )

        return self._run_engine(output_type, use_tqdm=use_tqdm)

    def _render_and_add_requests(
        self,
        prompts: Iterable[EngineInput],
        params: Sequence[SamplingParams | PoolingParams],
        *,
        lora_requests: Sequence[LoRARequest | None] | None = None,
        priorities: Sequence[int] | None = None,
    ) -> list[str]:
        with perfmark.region("vllm-002"):
            added_request_ids: list[str] = []

            try:
                for i, prompt in enumerate(prompts):
                    request_id = self._add_request(
                        prompt,
                        params[i],
                        lora_request=self._resolve_mm_lora(
                            prompt,
                            None if lora_requests is None else lora_requests[i],
                        ),
                        priority=0 if priorities is None else priorities[i],
                    )
                    added_request_ids.append(request_id)
            except Exception as e:
                if added_request_ids:
                    self.llm_engine.abort_request(added_request_ids, internal=True)
                raise e

            return added_request_ids

    def _add_request(
        self,
        prompt: EngineInput,
        params: SamplingParams | PoolingParams,
        lora_request: LoRARequest | None = None,
        priority: int = 0,
    ) -> str:
        if isinstance(params, SamplingParams):
            # We only care about the final output
            params.output_kind = RequestOutputKind.FINAL_ONLY

        request_id = str(next(self.request_counter))

        return self.llm_engine.add_request(
            request_id,
            prompt,
            params,
            lora_request=lora_request,
            priority=priority,
        )

    def _run_engine(
        self,
        output_type: type[_O] | tuple[type[_O], ...],
        *,
        use_tqdm: bool | Callable[..., tqdm] = True,
    ) -> list[_O]:
        # Initialize tqdm.
        if use_tqdm:
            num_requests = self.llm_engine.get_num_unfinished_requests()
            tqdm_func = use_tqdm if callable(use_tqdm) else tqdm
            pbar = tqdm_func(
                total=num_requests,
                desc="Processed prompts",
                dynamic_ncols=True,
                postfix=(f"est. speed input: {0:.2f} toks/s, output: {0:.2f} toks/s"),
            )

        # Run the engine.
        outputs: list[_O] = []
        total_in_toks = 0
        total_out_toks = 0
        while self.llm_engine.has_unfinished_requests():
            step_outputs = self.llm_engine.step()
            for output in step_outputs:
                assert isinstance(output, output_type)
                if output.finished:
                    outputs.append(output)  # type: ignore[arg-type]
                    if use_tqdm:
                        if isinstance(output, RequestOutput):
                            # Calculate tokens only for RequestOutput
                            n = len(output.outputs)
                            assert output.prompt_token_ids is not None
                            total_in_toks += len(output.prompt_token_ids) * n
                            in_spd = total_in_toks / pbar.format_dict["elapsed"]
                            total_out_toks += sum(
                                len(stp.token_ids) for stp in output.outputs
                            )
                            out_spd = total_out_toks / pbar.format_dict["elapsed"]
                            pbar.postfix = (
                                f"est. speed input: {in_spd:.2f} toks/s, "
                                f"output: {out_spd:.2f} toks/s"
                            )
                            pbar.update(n)
                        else:
                            pbar.update(1)
                        if pbar.n == num_requests:
                            pbar.refresh()

        if use_tqdm:
            pbar.close()
        # Sort the outputs by request ID.
        # This is necessary because some requests may be finished earlier than
        # its previous requests.
        return sorted(outputs, key=lambda x: int(x.request_id))

--- FILE: tests/test_case.py ---
"""Bounded correctness and reachability test for vllm-002."""
from driver import run

TARGET = "vllm-002"
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
# OfflineInferenceMixin._render_and_add_requests

Inspect the marked function in `vllm/entrypoints/offline_utils.py` at the pinned revision.
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
  "id": "vllm-002",
  "title": "OfflineInferenceMixin._render_and_add_requests body",
  "language": "python",
  "region": {
    "symbol": "OfflineInferenceMixin._render_and_add_requests",
    "start_line": 531,
    "end_line": 550,
    "kind": "function"
  },
  "marker": {
    "kind": "python-context",
    "name": "vllm-002",
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
    "path": "vllm/entrypoints/offline_utils.py",
    "sha256": "688fbad0af9c2180b83aa77dcd0dbda85ca076a6c72bffa61840896d950cf458"
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
