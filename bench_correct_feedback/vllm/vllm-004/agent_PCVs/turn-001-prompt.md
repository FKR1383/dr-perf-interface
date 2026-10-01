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

CASE: vllm-004
SANITIZED BENCHMARK:
--- FILE: vllm/v1/attention/backends/cpu_attn.py ---
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
import perfmark
import functools
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from vllm.config.cache import CacheDType

import torch

from vllm import _custom_ops as ops
from vllm import envs
from vllm.config import (
    VllmConfig,
    get_current_vllm_config,
    get_layers_from_vllm_config,
)
from vllm.logger import init_logger
from vllm.model_executor.layers.attention import Attention
from vllm.platforms import CpuArchEnum, current_platform
from vllm.utils.torch_utils import is_quantized_kv_cache
from vllm.v1.attention.backend import (
    AttentionBackend,
    AttentionImpl,
    AttentionLayer,
    AttentionMetadataBuilder,
    AttentionType,
    CommonAttentionMetadata,
    MultipleOf,
)
from vllm.v1.attention.backends.utils import (
    KVCacheLayoutType,
    get_num_attention_heads_from_layers,
)
from vllm.v1.kv_cache_interface import (
    AttentionSpec,
    CrossAttentionSpec,
    EncoderOnlyAttentionSpec,
)

logger = init_logger(__name__)


class CPUAttentionBackend(AttentionBackend):
    forward_includes_kv_cache_update: bool = False

    supported_dtypes: ClassVar[list[torch.dtype]] = [
        torch.float16,
        torch.bfloat16,
        torch.float32,
    ]
    supported_kv_cache_dtypes: ClassVar[list["CacheDType"]] = [
        "auto",
        "fp8",
        "fp8_e4m3",
        "fp8_e5m2",
    ]

    @staticmethod
    def get_supported_kernel_block_sizes() -> list[int | MultipleOf]:
        return [MultipleOf(16)]

    @classmethod
    def get_supported_head_sizes(cls) -> list[int]:
        return [32, 64, 80, 96, 112, 128, 160, 192, 224, 256, 512]

    @staticmethod
    def get_name() -> str:
        return "CPU_ATTN"

    @classmethod
    def supports_non_causal(cls) -> bool:
        return True

    @classmethod
    def supports_sliding_window(cls) -> bool:
        return True

    @classmethod
    def supports_attn_type(cls, attn_type: str) -> bool:
        """CPU attention supports decoder,
        encoder-only and encoder-decoder attention."""
        return attn_type in (
            AttentionType.DECODER,
            AttentionType.ENCODER,
            AttentionType.ENCODER_ONLY,
            AttentionType.ENCODER_DECODER,
        )

    @staticmethod
    def get_impl_cls() -> type["CPUAttentionBackendImpl"]:
        return CPUAttentionBackendImpl

    @staticmethod
    def get_builder_cls() -> type["CPUAttentionMetadataBuilder"]:
        return CPUAttentionMetadataBuilder

    @staticmethod
    def get_kv_cache_shape(
        num_blocks: int,
        block_size: int,
        num_kv_heads: int,
        head_size: int,
        cache_dtype_str: str = "auto",
    ) -> tuple[int, ...]:
        return num_blocks, num_kv_heads, block_size, 2 * head_size

    @classmethod
    def get_required_kv_cache_layout(cls) -> "KVCacheLayoutType | None":
        return "HND"

    @staticmethod
    def use_cascade_attention(*args, **kwargs) -> bool:
        return False


@dataclass
class CPUAttentionMetadata:
    num_actual_tokens: int  # Number of tokens excluding padding.
    max_query_len: int
    query_start_loc: torch.Tensor
    max_seq_len: int
    seq_lens: torch.Tensor
    block_table: torch.Tensor
    slot_mapping: torch.Tensor
    scheduler_metadata: torch.Tensor | None
    causal: bool = True
    dynamic_causal: torch.Tensor | None = None

    # can be removed after deprecate sdpa
    use_sdpa_prefill: bool = False
    num_decode_tokens: int = 0
    sdpa_attn_masks: list[torch.Tensor | None] | None = None
    sdpa_start_loc: torch.Tensor | None = None

    encoder_cache: torch.Tensor | None = None


class CPUAttentionMetadataBuilder(AttentionMetadataBuilder[CPUAttentionMetadata]):
    def __init__(
        self,
        kv_cache_spec: AttentionSpec,
        layer_names: list[str],
        vllm_config: VllmConfig,
        device: torch.device,
    ) -> None:
        super().__init__(kv_cache_spec, layer_names, vllm_config, device)

        self.kv_cache_spec = kv_cache_spec
        self.vllm_config = vllm_config

        parallel_config = vllm_config.parallel_config
        self.num_kv_heads = kv_cache_spec.num_kv_heads
        # The scheduler metadata built here sizes a scratchpad from the query
        # head count, so it must come from this group's layers: the model-wide
        # count is wrong for models that vary it per layer (e.g. Laguna).
        self.num_heads = get_num_attention_heads_from_layers(
            vllm_config, layer_names
        ) or vllm_config.model_config.get_num_attention_heads(parallel_config)
        self.head_dim = kv_cache_spec.head_size
        self.dtype = vllm_config.model_config.dtype
        self.window_size = self._group_sliding_window()
        self.block_size = vllm_config.cache_config.block_size
        self.kv_cache_dtype = vllm_config.cache_config.cache_dtype
        self.isa = _get_attn_isa(
            self.dtype,
            self.block_size,
            self.head_dim,
            self.kv_cache_dtype,
        )
        self.is_cross_attention = isinstance(kv_cache_spec, CrossAttentionSpec)
        self.is_encoder_only_attention = isinstance(
            kv_cache_spec, EncoderOnlyAttentionSpec
        )

    def _group_sliding_window(self) -> int:
        """The window shared by every layer in this group, else -1 (no window).

        Taken from the layers rather than the group spec: one KV cache group can
        hold both windowed and global layers (e.g. Gemma-3 with the hybrid KV
        cache manager disabled), and the scheduler metadata built here is shared
        by the whole group, so it may only assume a window all of them agree on.
        """
        layers = get_layers_from_vllm_config(
            self.vllm_config, Attention, self.layer_names
        )
        windows = {
            layer.impl.sliding_window
            for layer in layers.values()
            if isinstance(layer.impl, CPUAttentionBackendImpl)
        }
        if len(windows) != 1:
            return -1
        window = windows.pop()
        return -1 if window is None else window

    def build(
        self,
        common_prefix_len: int,
        common_attn_metadata: CommonAttentionMetadata,
        fast_build: bool = False,
    ) -> CPUAttentionMetadata:
        num_reqs = common_attn_metadata.num_reqs
        num_actual_tokens = common_attn_metadata.num_actual_tokens
        max_query_len = common_attn_metadata.max_query_len
        max_seq_len = common_attn_metadata.max_seq_len
        query_start_loc = common_attn_metadata.query_start_loc
        seq_lens = common_attn_metadata.seq_lens
        block_table_tensor = common_attn_metadata.block_table_tensor
        slot_mapping = common_attn_metadata.slot_mapping
        is_dynamic_casual = isinstance(common_attn_metadata.causal, torch.Tensor)
        dynamic_casual = None
        if is_dynamic_casual:
            dynamic_casual = common_attn_metadata.causal

        causal = (
            False
            if self.is_cross_attention or is_dynamic_casual
            else common_attn_metadata.causal
        )

        encoder_cache_tensor = None
        if self.is_encoder_only_attention:
            block_nums = (seq_lens + self.block_size - 1) // self.block_size
            start_block_ids = torch.zeros_like(seq_lens)
            torch.cumsum(block_nums[:-1], 0, out=start_block_ids[1:])
            total_block_num: int = block_nums.sum().item()
            max_block_num = block_nums.max().item()
            block_offsets = torch.arange(
                0, max_block_num, dtype=block_table_tensor.dtype
            )
            encoder_block_table = start_block_ids[:, None] + block_offsets[None, :]
            torch.ops._C.compute_slot_mapping_kernel_impl(
                query_start_loc,
                common_attn_metadata.positions,
                encoder_block_table,
                slot_mapping,
                self.block_size,
            )
            encoder_cache_tensor = torch.zeros(
                (
                    total_block_num,
                    self.num_kv_heads,
                    self.block_size,
                    2 * self.head_dim,
                ),
                dtype=self.dtype,
            )
            block_table_tensor = encoder_block_table

        scheduler_metadata = ops.cpu_attn_get_scheduler_metadata(
            num_reqs=num_reqs,
            num_heads=self.num_heads,
            num_kv_heads=self.num_kv_heads,
            head_dim=self.head_dim,
            seq_lens=seq_lens,
            dtype=self.dtype,
            query_start_loc=query_start_loc,
            causal=causal,
            sliding_window_size=self.window_size,
            isa=self.isa,
            enable_kv_split=envs.VLLM_CPU_ATTN_SPLIT_KV,
            dynamic_causal=dynamic_casual,
            kv_cache_dtype=self.kv_cache_dtype,
        )

        attn_metadata = CPUAttentionMetadata(
            num_actual_tokens=num_actual_tokens,
            max_query_len=max_query_len,
            query_start_loc=query_start_loc,
            max_seq_len=max_seq_len,
            seq_lens=seq_lens,
            block_table=block_table_tensor,
            slot_mapping=slot_mapping,
            scheduler_metadata=scheduler_metadata,
            causal=causal,
            encoder_cache=encoder_cache_tensor,
            dynamic_causal=dynamic_casual,
        )

        return attn_metadata


class CPUAttentionBackendImpl(AttentionImpl):
    def __init__(
        self,
        num_heads: int,
        head_size: int,
        scale: float,
        num_kv_heads: int,
        alibi_slopes: list[float] | None,
        sliding_window: int | None,
        kv_cache_dtype: str,
        logits_soft_cap: float | None = None,
        attn_type: str = AttentionType.DECODER,
        kv_sharing_target_layer_name: str | None = None,
        sinks: torch.Tensor | None = None,
    ) -> None:
        self.kv_sharing_target_layer_name = kv_sharing_target_layer_name
        self.num_heads = num_heads
        self.head_size = head_size
        self.scale = float(scale)
        if logits_soft_cap is not None and attn_type in (
            AttentionType.ENCODER,
            AttentionType.ENCODER_ONLY,
        ):
            logger.warning_once(
                "CPU_ATTN does not support logits softcap for"
                " ENCODER and ENCODER_ONLY, outputs may be slightly off"
            )
        if logits_soft_cap is None:
            logits_soft_cap = 0
        self.logits_soft_cap = logits_soft_cap

        self.num_kv_heads = num_kv_heads
        if alibi_slopes is not None:
            alibi_slopes = torch.tensor(alibi_slopes, dtype=torch.float32)
        self.alibi_slopes = alibi_slopes
        if sliding_window is None:
            self.sliding_window = -1
        else:
            self.sliding_window = sliding_window
        self.kv_cache_dtype = kv_cache_dtype
        self.num_queries_per_kv = self.num_heads // self.num_kv_heads

        self.is_fp8_kv_cache = is_quantized_kv_cache(kv_cache_dtype)
        self.attn_type = attn_type

        self.sinks = sinks
        if self.sinks is not None:
            assert self.sinks.shape[0] == num_heads, (
                "Sinks must have the same number of heads as the number of "
                "heads in the layer"
            )

        vllm_config = get_current_vllm_config()
        self.isa = _get_attn_isa(
            vllm_config.model_config.dtype,
            vllm_config.cache_config.block_size,
            self.head_size,
            self.kv_cache_dtype,
        )

    def forward(
        self,
        layer: AttentionLayer,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        kv_cache: torch.Tensor,
        attn_metadata: CPUAttentionMetadata | None,
        output: torch.Tensor,
        output_scale: torch.Tensor | None = None,
        output_block_scale: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Forward pass for CPU attention backend.

        Args:
            query: shape = [num_tokens, num_heads, head_size]
            key: shape = [num_tokens, num_kv_heads, head_size]
            value: shape = [num_tokens, num_kv_heads, head_size]
            kv_cache: shape =
                [num_blocks, num_kv_heads, block_size, 2 * head_size]
            attn_metadata: Metadata for attention.
        Returns:
            shape = [num_tokens, num_heads * head_size]
        """
        with perfmark.region("vllm-004"):
            if output_scale is not None or output_block_scale is not None:
                raise NotImplementedError(
                    "fused output quantization is not yet supported"
                    " for CPUAttentionBackendImpl"
                )

            # For warming-up
            if attn_metadata is None:
                return output

            num_actual_tokens = attn_metadata.num_actual_tokens

            is_encoder_attention = self.attn_type in (
                AttentionType.ENCODER_ONLY,
                AttentionType.ENCODER,
            )
            if is_encoder_attention:
                # For encoder attention,
                kv_cache = attn_metadata.encoder_cache

            # KV cache size are [num_blocks, num_kv_heads, block_size,
            # 2 * head_size]. Make a view [num_blocks, num_kv_heads,
            # block_size * 2, head_size]. Then slice KV at dim 2
            num_blocks, num_kv_heads, block_size, _ = kv_cache.size()
            kv_cache = kv_cache.view((num_blocks, num_kv_heads, block_size * 2, -1))
            key_cache, value_cache = kv_cache.chunk(2, dim=2)

            if is_encoder_attention:
                ops.cpu_attn_reshape_and_cache(
                    key,
                    value,
                    key_cache,
                    value_cache,
                    attn_metadata.slot_mapping,
                    self.isa,
                    k_scale=layer._k_scale_float,
                    v_scale=layer._v_scale_float,
                    kv_cache_dtype=self.kv_cache_dtype,
                )

            ops.cpu_attention_with_kv_cache(
                query=query[:num_actual_tokens],
                key_cache=key_cache,
                value_cache=value_cache,
                output=output[:num_actual_tokens],  # type: ignore
                query_start_loc=attn_metadata.query_start_loc,
                seq_lens=attn_metadata.seq_lens,
                scale=self.scale,
                causal=attn_metadata.causal,
                alibi_slopes=self.alibi_slopes,  # type: ignore
                sliding_window=self.sliding_window,
                block_table=attn_metadata.block_table,
                softcap=self.logits_soft_cap,
                scheduler_metadata=attn_metadata.scheduler_metadata,
                s_aux=self.sinks,
                dynamic_causal=attn_metadata.dynamic_causal,
                k_scale=layer._k_scale_float,
                v_scale=layer._v_scale_float,
                kv_cache_dtype=self.kv_cache_dtype,
            )

            return output

    def do_kv_cache_update(
        self,
        layer: torch.nn.Module,
        key: torch.Tensor,
        value: torch.Tensor,
        kv_cache: torch.Tensor,
        slot_mapping: torch.Tensor,
    ) -> None:
        if self.attn_type in (AttentionType.ENCODER_ONLY, AttentionType.ENCODER):
            return

        num_blocks, num_kv_heads, block_size, _ = kv_cache.size()
        kv_cache = kv_cache.view((num_blocks, num_kv_heads, block_size * 2, -1))
        key_cache, value_cache = kv_cache.chunk(2, dim=2)
        ops.cpu_attn_reshape_and_cache(
            key,
            value,
            key_cache,
            value_cache,
            slot_mapping,
            self.isa,
            k_scale=layer._k_scale_float,
            v_scale=layer._v_scale_float,
            kv_cache_dtype=self.kv_cache_dtype,
        )


@functools.lru_cache(maxsize=1)
def _riscv_supports_rvv() -> bool:
    """Whether the C++ RVV attention path is usable.

    The kernel in csrc/cpu/cpu_attn_rvv.hpp uses VLEN-agnostic RVVI()
    macros and supports VLEN=128 and VLEN=256.  CMake auto-detects the
    largest zvl<N>b from /proc/cpuinfo and passes it via -mrvv-vector-bits.
    The RVV path is compiled whenever __riscv_v_min_vlen is defined, so
    we check that at least one supported zvl<N>b is advertised.
    """
    # The C++ compile-time check is the ground truth: it knows which
    # VLEN the binary was actually compiled for.  The cpuinfo check
    # below is only a fast-path shortcut.
    try:
        import torch

        if torch.ops._C.cpu_attn_has_isa("rvv"):
            return True
    except Exception:
        pass

    # Fallback: check /proc/cpuinfo for zvl128b/zvl256b.
    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()
    except OSError:
        return False
    return any(f"zvl{n}b" in cpuinfo for n in (128, 256))


def _get_attn_isa(
    dtype: torch.dtype,
    block_size: int,
    head_size: int | None = None,
    kv_cache_dtype: str | None = None,
) -> str:
    fp8_kv = is_quantized_kv_cache(kv_cache_dtype) if kv_cache_dtype else False
    if head_size is not None and head_size % 32 != 0 and head_size % 16 == 0:
        if fp8_kv:
            raise NotImplementedError(
                "FP8 KV cache requires head_size divisible by 32 on CPU."
            )
        return "vec16"
    supports_amx = torch.cpu._is_amx_tile_supported()
    arch = current_platform.get_cpu_architecture()
    supports_arm = arch == CpuArchEnum.ARM
    supports_vxe = arch == CpuArchEnum.S390X
    supports_riscv = arch == CpuArchEnum.RISCV
    supports_vsx = arch == CpuArchEnum.POWERPC
    supports_avx512 = torch.cpu._is_avx512_supported()
    if fp8_kv and not supports_amx and not supports_avx512:
        raise NotImplementedError(
            "FP8 KV cache on CPU requires x86 with AVX-512 or AMX."
        )
    if supports_amx and dtype in (torch.bfloat16,) and block_size % 32 == 0:
        return "amx"
    elif block_size % 32 == 0:
        if supports_arm:
            # support ARM NEON FMLA and BFMMLA (bf16) for block size 32
            return "neon"
        elif supports_riscv and _riscv_supports_rvv():
            return "rvv"
        elif supports_vxe:
            return "vxe"
        elif supports_vsx:
            return "vsx"
        else:
            return "vec"
    else:
        return "vec16"

--- FILE: tests/test_case.py ---
"""Bounded correctness and reachability test for vllm-004."""
from driver import run

TARGET = "vllm-004"
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
# CPUAttentionBackendImpl.forward

Inspect the marked function in `vllm/v1/attention/backends/cpu_attn.py` at the pinned revision.
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
  "id": "vllm-004",
  "title": "CPUAttentionBackendImpl.forward body",
  "language": "python",
  "region": {
    "symbol": "CPUAttentionBackendImpl.forward",
    "start_line": 369,
    "end_line": 430,
    "kind": "function"
  },
  "marker": {
    "kind": "python-context",
    "name": "vllm-004",
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
    "path": "vllm/v1/attention/backends/cpu_attn.py",
    "sha256": "b4f45daf2c39b7537f4615cb1fd5c406e0f4dddfdbc1e6ce0d08a479d2a53c49"
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
