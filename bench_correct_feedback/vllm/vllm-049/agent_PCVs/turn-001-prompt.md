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

CASE: vllm-049
SANITIZED BENCHMARK:
--- FILE: vllm/v1/request.py ---
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project

import perfmark
import enum
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import torch

from vllm.multimodal.inputs import MultiModalFeatureSpec
from vllm.pooling_params import PoolingParams
from vllm.sampling_params import SamplingParams
from vllm.utils import length_from_prompt_token_ids_or_embeds
from vllm.v1.engine import (
    EngineCoreEvent,
    EngineCoreEventType,
    EngineCoreRequest,
    FinishReason,
)
from vllm.v1.metrics.stats import PrefillStats
from vllm.v1.structured_output.request import StructuredOutputRequest
from vllm.v1.utils import ConstantList

if TYPE_CHECKING:
    from vllm.lora.request import LoRARequest
    from vllm.v1.core.kv_cache_utils import BlockHash


@dataclass
class StreamingUpdate:
    """Lightweight data for streaming session continuation.

    Contains only the fields needed to update an existing streaming session
    with new input data.
    """

    mm_features: list[MultiModalFeatureSpec] | None
    prompt_token_ids: list[int] | None
    max_tokens: int
    arrival_time: float
    sampling_params: SamplingParams | None

    @classmethod
    def from_request(cls, request: "Request") -> "StreamingUpdate | None":
        if not request.resumable:
            return None
        return cls(
            mm_features=request.mm_features,
            prompt_token_ids=request.prompt_token_ids,
            max_tokens=request.max_tokens,
            arrival_time=request.arrival_time,
            sampling_params=request.sampling_params,
        )


class Request:
    def __init__(
        self,
        request_id: str,
        prompt_token_ids: list[int] | None,
        sampling_params: SamplingParams | None,
        pooling_params: PoolingParams | None,
        client_index: int = 0,
        arrival_time: float | None = None,
        prompt_embeds: torch.Tensor | None = None,
        prompt_is_token_ids: list[bool] | None = None,
        mm_features: list[MultiModalFeatureSpec] | None = None,
        lora_request: "LoRARequest | None" = None,
        cache_salt: str | None = None,
        priority: int = 0,
        trace_headers: Mapping[str, str] | None = None,
        block_hasher: Callable[["Request"], list["BlockHash"]] | None = None,
        resumable: bool = False,
        session_id: str | None = None,
        reasoning_ended: bool | None = None,
        reasoning_parser_kwargs: dict[str, Any] | None = None,
        abort_immediately: bool = False,
    ) -> None:
        with perfmark.region("vllm-049"):
            self.request_id = request_id
            self.client_index = client_index
            self.priority = priority
            self.sampling_params = sampling_params
            self.pooling_params = pooling_params
            self.lora_request = lora_request
            self.structured_output_request = StructuredOutputRequest.from_sampling_params(
                sampling_params
            )
            if self.structured_output_request is not None:
                self.structured_output_request.reasoning_ended = reasoning_ended
                self.structured_output_request.reasoning_parser_kwargs = (
                    reasoning_parser_kwargs
                )
            self.arrival_time = arrival_time if arrival_time is not None else time.time()

            self.status = RequestStatus.WAITING
            self.events: list[EngineCoreEvent] = []
            self.stop_reason: int | str | None = None

            # P/D: Connector-specific KV transfer parameters.
            self.kv_transfer_params: dict[str, Any] | None = None
            # E/P/D: Connector-specific encoder-cache transfer parameters.
            self.ec_transfer_params: dict[str, Any] | None = None

            if pooling_params is not None:
                # Pooling models.
                self.max_tokens = 1
            elif sampling_params is not None:
                # Generative models.
                assert sampling_params.max_tokens is not None
                self.max_tokens = sampling_params.max_tokens
                if self.structured_output_request is not None:
                    self.status = RequestStatus.WAITING_FOR_STRUCTURED_OUTPUT_GRAMMAR

                if sampling_params.extra_args is not None:
                    self.kv_transfer_params = sampling_params.extra_args.get(
                        "kv_transfer_params"
                    )
                    self.ec_transfer_params = sampling_params.extra_args.get(
                        "ec_transfer_params"
                    )
                    self.kv_cache_report_mode = sampling_params.extra_args.get(
                        "kv_cache_report_mode", "incremental"
                    )
                else:
                    self.kv_cache_report_mode = "incremental"
            else:
                raise ValueError("sampling_params and pooling_params can't both be unset")

            self.prompt_token_ids = prompt_token_ids
            self.prompt_embeds = prompt_embeds
            # Per-position mask used in mixed-mode (chat completion with
            # prompt_embeds). `None` except when both `prompt_token_ids` and
            # `prompt_embeds` are set and their positions are interleaved.
            self.prompt_is_token_ids = prompt_is_token_ids
            # Cache per-block prompt-embed hashes to avoid rehashing the same
            # tensor slices when generating extra keys.
            self._prompt_embeds_per_block_hashes: dict[tuple[int, int], bytes] = {}
            self.num_prompt_tokens = length_from_prompt_token_ids_or_embeds(
                prompt_token_ids, prompt_embeds
            )
            self._output_token_ids: list[int] = []
            self._all_token_ids: list[int] = (
                self.prompt_token_ids.copy()
                if self.prompt_token_ids is not None
                else [0] * self.num_prompt_tokens
            )

            # Used in async scheduling.
            self.num_output_placeholders = 0
            # Tokens of output in flight when the request was preempted: delivered
            # on return, but must not mutate the reset counters.
            self.num_stale_output_tokens = 0
            # Drop the stale output instead, for same-step preempt + resume
            # (reset_prefix_cache).
            self.drop_stale_output = False

            # Tokens of steps whose output is not yet processed (async scheduling
            # and PP run ahead of the GPU); `num_computed_tokens` counts them
            # optimistically.
            self.num_in_flight_tokens = 0

            # V2+PP+async: Enforces `pp_size` cadence between same-request decode steps
            # so the worker's broadcast slot ring stays consistent.
            self.next_decode_eligible_step = 0

            # Seq of the most recent step this request was scheduled in; fences
            # deferred block freeing (see Scheduler._free_request_blocks).
            self.last_sched_seq = 0

            self.spec_token_ids: list[int] = []
            self.num_computed_tokens = 0
            self.cache_salt: str | None = cache_salt

            # Multi-modal related
            self.mm_features = mm_features or []

            # Read-only views
            # Prevent directly appending to these lists since
            # they should also be updated simultaneously.
            self.output_token_ids = ConstantList(self._output_token_ids)
            self.all_token_ids = ConstantList(self._all_token_ids)
            # trace_headers
            self.trace_headers = trace_headers
            self.session_id = session_id

            # True if this request is scheduled as a non-final prefill chunk.
            self.is_prefill_chunk = False

            # Block-aligned token position of a proven shared prefix worth pinning
            # in the (sparse) prefix cache; 0 means none. Set at admission for
            # hybrid/Mamba models when a shared prefix is detected (Marconi-style).
            self.shared_prefix_boundary = 0

            # The number of NaNs in logits. A value greater than 0
            # indicates that the output is corrupted
            self.num_nans_in_logits = 0

            # The number of times this request has been preempted by the scheduler.
            self.num_preemptions = 0

            self.prefill_stats: PrefillStats | None = PrefillStats()

            self.block_hashes: list[BlockHash] = []
            # Store the block hasher without binding self to avoid creating a
            # reference cycle (Request -> partial -> Request) that prevents
            # immediate garbage collection via reference counting.
            self._block_hasher: Callable[[Request], list[BlockHash]] | None = block_hasher
            self.update_block_hashes()

            self.skip_reading_prefix_cache = self.get_skip_reading_prefix_cache()

            # Used for streaming
            self.resumable = resumable
            # None entry in the queue means finished.
            self.streaming_queue: deque[StreamingUpdate | None] | None = None

            # If True, request should be aborted immediately after being added to
            # the scheduler so the connector's request_finished hook runs.
            self.abort_immediately = abort_immediately

    @classmethod
    def from_engine_core_request(
        cls,
        request: EngineCoreRequest,
        block_hasher: Callable[["Request"], list["BlockHash"]] | None,
    ) -> "Request":
        return cls(
            request_id=request.request_id,
            client_index=request.client_index,
            prompt_token_ids=request.prompt_token_ids,
            prompt_embeds=request.prompt_embeds,
            prompt_is_token_ids=request.prompt_is_token_ids,
            mm_features=request.mm_features,
            sampling_params=request.sampling_params,
            pooling_params=request.pooling_params,
            arrival_time=request.arrival_time,
            lora_request=request.lora_request,
            cache_salt=request.cache_salt,
            priority=request.priority,
            trace_headers=request.trace_headers,
            block_hasher=block_hasher,
            resumable=request.resumable,
            session_id=request.session_id,
            reasoning_ended=request.reasoning_ended,
            reasoning_parser_kwargs=request.reasoning_parser_kwargs,
            abort_immediately=request.abort_immediately,
        )

    def append_output_token_ids(
        self,
        token_ids: int | list[int],
    ) -> None:
        if isinstance(token_ids, int):
            self._output_token_ids.append(token_ids)
            self._all_token_ids.append(token_ids)
        else:
            self._output_token_ids.extend(token_ids)
            self._all_token_ids.extend(token_ids)

        self.update_block_hashes()

    def update_block_hashes(self) -> None:
        """Compute block hashes for any new full blocks and append them."""
        if self._block_hasher is not None:
            self.block_hashes.extend(self._block_hasher(self))

    @property
    def use_structured_output(self) -> bool:
        return self.structured_output_request is not None

    @property
    def num_tokens(self) -> int:
        return len(self._all_token_ids)

    @property
    def num_tokens_with_spec(self) -> int:
        return len(self._all_token_ids) + len(self.spec_token_ids)

    @property
    def num_output_tokens(self) -> int:
        return len(self._output_token_ids)

    @property
    def num_encoder_inputs(self) -> int:
        return len(self.mm_features)

    @property
    def has_encoder_inputs(self) -> bool:
        return self.num_encoder_inputs > 0

    def get_skip_reading_prefix_cache(self) -> bool:
        if (
            self.sampling_params is not None
            and self.sampling_params.skip_reading_prefix_cache is not None
        ):
            return self.sampling_params.skip_reading_prefix_cache
        elif (
            self.pooling_params is not None
            and self.pooling_params.skip_reading_prefix_cache is not None
        ):
            return self.pooling_params.skip_reading_prefix_cache
        return False

    def is_finished(self) -> bool:
        return RequestStatus.is_finished(self.status)

    def get_finished_reason(self) -> FinishReason | None:
        return RequestStatus.get_finished_reason(self.status)

    def get_num_encoder_embeds(self, input_id: int) -> int:
        assert input_id < len(self.mm_features)
        return self.mm_features[input_id].mm_position.get_num_embeds()

    def record_event(
        self,
        event_type: EngineCoreEventType,
        timestamp: float | None = None,
    ) -> None:
        self.events.append(EngineCoreEvent.new_event(event_type, timestamp))

    def take_events(self) -> list[EngineCoreEvent] | None:
        if not self.events:
            return None
        events, self.events = self.events, []
        return events

    def take_prefill_stats(self) -> PrefillStats | None:
        if self.prefill_stats is None:
            return None
        prefill_stats = self.prefill_stats
        self.prefill_stats = None
        return prefill_stats

    def __lt__(self, other: "Request") -> bool:
        """
        Compare two requests based on priority, arrival time, and request ID.
        Used in priority scheduling.
        """
        if self.priority != other.priority:
            return self.priority < other.priority
        if self.arrival_time != other.arrival_time:
            return self.arrival_time < other.arrival_time
        if self.request_id != other.request_id:
            return self.request_id < other.request_id
        return id(self) < id(other)


class RequestStatus(enum.IntEnum):
    """Status of a request."""

    WAITING = enum.auto()
    WAITING_FOR_STRUCTURED_OUTPUT_GRAMMAR = enum.auto()
    WAITING_FOR_REMOTE_KVS = enum.auto()
    WAITING_FOR_STREAMING_REQ = enum.auto()
    RUNNING = enum.auto()
    PREEMPTED = enum.auto()
    # Note: anything after PREEMPTED will be considered
    # as a finished status.
    FINISHED_STOPPED = enum.auto()
    FINISHED_LENGTH_CAPPED = enum.auto()
    FINISHED_ABORTED = enum.auto()
    FINISHED_IGNORED = enum.auto()
    FINISHED_ERROR = enum.auto()
    FINISHED_REPETITION = enum.auto()

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def is_finished(status: "RequestStatus") -> bool:
        return status > RequestStatus.PREEMPTED

    @staticmethod
    def get_finished_reason(status: "RequestStatus") -> FinishReason | None:
        return _FINISHED_REASON_MAP.get(status)


# Mapping of finished statuses to their finish reasons.
# NOTE: The ignored requests are the requests whose prompt lengths
# are longer than the model's length cap. Therefore, the stop
# reason should also be "length" as in OpenAI API.
_FINISHED_REASON_MAP = {
    RequestStatus.FINISHED_STOPPED: FinishReason.STOP,
    RequestStatus.FINISHED_LENGTH_CAPPED: FinishReason.LENGTH,
    RequestStatus.FINISHED_ABORTED: FinishReason.ABORT,
    RequestStatus.FINISHED_IGNORED: FinishReason.LENGTH,
    RequestStatus.FINISHED_ERROR: FinishReason.ERROR,
    RequestStatus.WAITING_FOR_STREAMING_REQ: FinishReason.STOP,
    RequestStatus.FINISHED_REPETITION: FinishReason.REPETITION,
}

--- FILE: tests/test_case.py ---
"""Bounded correctness and reachability test for vllm-049."""
from driver import run

TARGET = "vllm-049"
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
# Request.__init__

Inspect the marked function in `vllm/v1/request.py` at the pinned revision.
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
  "id": "vllm-049",
  "title": "Request.__init__ body",
  "language": "python",
  "region": {
    "symbol": "Request.__init__",
    "start_line": 82,
    "end_line": 222,
    "kind": "function"
  },
  "marker": {
    "kind": "python-context",
    "name": "vllm-049",
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
    "path": "vllm/v1/request.py",
    "sha256": "0287844f70eeaeb077d714e833a4b449a15e045a6516f8530182e357a5bec82f"
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
      "status": "region-verified",
      "details": "Value assertions passed and Probe.finish observed the exact marker after applying this case patch alone to a detached-file hardlink clone of the pinned checkout."
    },
    "coverage_note": "Directly invokes the marked Python function with several bounded inputs; exact marker reachability was verified with this individual patch."
  }
}
