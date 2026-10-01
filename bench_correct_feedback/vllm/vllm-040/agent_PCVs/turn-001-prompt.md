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

CASE: vllm-040
SANITIZED BENCHMARK:
--- FILE: vllm/v1/core/single_type_kv_cache_manager.py ---
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
import perfmark
import itertools
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence
from typing import ClassVar

from vllm.utils.math_utils import cdiv
from vllm.v1.core.block_pool import BlockPool
from vllm.v1.core.kv_cache_utils import (
    BlockHashList,
    BlockHashListWithBlockSize,
    BlockHashWithGroupId,
    KVCacheBlock,
    resolve_block_hashes,
)
from vllm.v1.kv_cache_interface import (
    AttentionSpec,
    ChunkedLocalAttentionSpec,
    CrossAttentionSpec,
    FullAttentionSpec,
    HiddenStateCacheSpec,
    KVCacheSpec,
    MambaSpec,
    MLAAttentionSpec,
    RSWASpec,
    SinkFullAttentionSpec,
    SlidingWindowMLASpec,
    SlidingWindowSpec,
)
from vllm.v1.kv_cache_spec_registry import KVCacheSpecRegistry
from vllm.v1.request import Request


class SingleTypeKVCacheManager(ABC):
    """
    An abstract base class for a manager that handle the kv cache management
    logic of one specific type of attention layer.
    """

    supports_fine_grained_hash_lookup: ClassVar[bool] = False

    def __init__(
        self,
        kv_cache_spec: KVCacheSpec,
        block_pool: BlockPool,
        enable_caching: bool,
        kv_cache_group_id: int,
        scheduler_block_size: int,
        dcp_world_size: int = 1,
        pcp_world_size: int = 1,
        needs_kv_cache_zeroing: bool = False,
        max_admission_blocks_per_request: int | None = None,
    ) -> None:
        """
        Initializes the SingleTypeKVCacheManager.
        Args:
            kv_cache_spec: The kv_cache_spec for this manager.
            block_pool: The block pool.
            kv_cache_group_id: The id of the kv cache group of this manager.
            scheduler_block_size: The scheduling granularity (LCM of all group
                block sizes); a multiple of this manager's ``block_size``.
            needs_kv_cache_zeroing: Whether worker-side KV cache zeroing needs
                newly allocated block IDs from this manager.
            max_admission_blocks_per_request: Recycling-aware per-request
                block cap used by `get_num_blocks_to_allocate`. Only set for
                spec types that recycle blocks across chunks (SWA,
                chunked-local); `None` (the default) means no cap, which is
                correct for full-attention-style specs that hold every
                block until the request finishes.
        """
        self.scheduler_block_size = scheduler_block_size
        # The block size for this manager; used for actual block allocation.
        self.block_size = kv_cache_spec.block_size
        self.dcp_world_size = dcp_world_size
        self.pcp_world_size = pcp_world_size
        if dcp_world_size > 1:
            self.block_size *= dcp_world_size
        self.kv_cache_spec = kv_cache_spec
        self.block_pool = block_pool
        self.enable_caching = enable_caching
        self._max_admission_blocks_per_request = max_admission_blocks_per_request
        # Record newly allocated block ids only when worker-side zeroing will
        # consume them and this manager holds a spec type that gets zeroed.
        self._record_new_block_ids = needs_kv_cache_zeroing and isinstance(
            kv_cache_spec, AttentionSpec
        )
        self.new_block_ids: list[int] = []

        # Mapping from request ID to blocks to track the blocks allocated
        # for each request, so that we can free the blocks when the request
        # is finished.
        self.req_to_blocks: defaultdict[str, list[KVCacheBlock]] = defaultdict(list)

        # {req_id: The number of cached blocks for this given request}
        # This is used to track the number of cached blocks for each request.
        # This is only used to track the RUNNING requests, we do not track the
        # data for preempted ones.
        self.num_cached_block: dict[str, int] = {}

        self.kv_cache_group_id = kv_cache_group_id
        self._null_block = block_pool.null_block

        # Whether this group's prefix-cache hits drop the EAGLE/MTP lookahead
        # block. Only consulted by managers whose hit logic is sparse within an
        # aligned segment (SWA). Initialized lazily by the coordinator after
        # determining the attention groups.
        self.use_eagle = False

        # Partial-hit copy-on-write bookkeeping. Populated only by fine-grained
        # managers (full attention, mamba "align"); harmlessly empty elsewhere.
        self._partial_hit_reqs: dict[str, tuple[int, KVCacheBlock]] = {}
        self._pending_cow_copies: list[tuple[KVCacheBlock, KVCacheBlock]] = []
        # Partial-tail offload hand-off for external KV connectors: when a
        # producer registers its last-prompt-boundary partial tail and the
        # durable boundary block is not on the append-only request block table
        # (mamba "align" CoW target), record the request, group, block, and
        # exact token boundary so a connector can offload it under the right
        # hash. Populated only by mamba "align".
        self._pending_partial_tail_offloads: list[
            tuple[str, int, KVCacheBlock, int]
        ] = []

    @classmethod
    def _get_num_evictable_blocks(cls, blocks: Sequence[KVCacheBlock]):
        return sum(blk.ref_cnt == 0 and not blk.is_null for blk in blocks)

    def _has_partial_local_hit(
        self,
        new_computed_blocks: Sequence[KVCacheBlock],
        num_local_computed_tokens: int,
    ) -> bool:
        # The local prefix-cache hit ends inside one of this manager's
        # blocks: the shared tail block needs CoW.
        return (
            len(new_computed_blocks) > 0
            and num_local_computed_tokens % self.block_size != 0
        )

    def get_num_blocks_to_allocate(
        self,
        request_id: str,
        num_tokens: int,
        new_computed_blocks: Sequence[KVCacheBlock],
        total_computed_tokens: int,
        num_local_computed_tokens: int,
        num_tokens_main_model: int,
        apply_admission_cap: bool = False,
    ) -> int:
        """
        Get the number of blocks needed to be allocated for the request.

        Args:
            request_id: The request ID.
            num_tokens: The total number of tokens that need a slot (including
                tokens that are already allocated).
            new_computed_blocks: The new computed blocks just hitting the
                prefix caching.
            total_computed_tokens: Include both local and external computed
                tokens.
            num_local_computed_tokens: The number of local prefix-cache computed
                tokens.
            num_tokens_main_model: The number of tokens for the main model (aka target
                model in spec decode). w/o spec decode, it is num_tokens;
                with spec decode, it is num_tokens - num_lookahead_tokens.
            apply_admission_cap: If True, clamp by `num_required_blocks` by
                `_max_admission_blocks_per_request`for recycling-aware specs
                (SWA, chunked-local).

        Returns:
            The number of blocks to allocate.
        """

        num_required_blocks = cdiv(num_tokens, self.block_size)
        if apply_admission_cap and self._max_admission_blocks_per_request is not None:
            # Recycling-aware specs (SWA, chunked-local) cap the per-request
            # reservation here so admission matches the startup pool sizer
            # (`SlidingWindowSpec.max_admission_blocks_per_request` / its
            # chunked-local counterpart). `remove_skipped_blocks` runs from
            # `allocate_slots` before each chunk's `get_num_blocks_to_allocate`,
            # so per-request peak real-held blocks <= this cap, which keeps
            # `sum(reservations) <= pool` <=> `sum(peak_real_held) <= pool`.
            # Drift between the two would re-introduce the deadlock from
            # issue #39734 or, worse, mid-prefill OOM.
            num_required_blocks = min(
                num_required_blocks, self._max_admission_blocks_per_request
            )
        num_req_blocks = len(self.req_to_blocks.get(request_id, ()))

        if request_id in self.num_cached_block:
            # Fast-path: a running request won't have any new prefix-cache hits.
            assert len(new_computed_blocks) == 0
            # NOTE: With speculative decoding, request's blocks may be allocated
            # for draft tokens which are later rejected. In this case,
            # num_required_blocks may be smaller than num_req_blocks.
            return max(num_required_blocks - num_req_blocks, 0)

        num_skipped_tokens = self.get_num_skipped_tokens(total_computed_tokens)
        num_local_computed_blocks = len(new_computed_blocks) + num_req_blocks
        # Number of whole blocks that are skipped by the attention window.
        # If nothing is skipped, this is 0.
        num_skipped_blocks = num_skipped_tokens // self.block_size
        # We need blocks for the non-skipped suffix. If there are still
        # local-computed blocks inside the window, they contribute to the
        # required capacity; otherwise, skipped blocks dominate.
        num_new_blocks = max(
            num_required_blocks - max(num_skipped_blocks, num_local_computed_blocks),
            0,
        )

        # Among the `new_computed_blocks`, the first `num_skipped_blocks` worth
        # of blocks are skipped; `num_req_blocks` of those may already be in
        # `req_to_blocks`, so only skip the remainder from `new_computed_blocks`.
        num_skipped_new_computed_blocks = max(0, num_skipped_blocks - num_req_blocks)

        # If a computed block is an eviction candidate (in the free queue and
        # ref_cnt == 0), it will be removed from the free queue when touched by
        # the allocated request, so we must count it in the free-capacity check.
        num_evictable_blocks = self._get_num_evictable_blocks(
            new_computed_blocks[num_skipped_new_computed_blocks:]
        )
        if self._has_partial_local_hit(new_computed_blocks, num_local_computed_tokens):
            # Reserve the extra block that allocate_new_blocks pulls for the
            # partial-hit CoW redirect.
            num_new_blocks += 1
        return num_new_blocks + num_evictable_blocks

    def add_local_computed_blocks(
        self,
        request_id: str,
        new_computed_blocks: Sequence[KVCacheBlock],
        num_local_computed_tokens: int,
        num_external_computed_tokens: int,
    ) -> None:
        """
        Add the locally cached (prefix-hit) blocks to the request:
        1. Touch the computed blocks (paired with adding them to `req_blocks`)
           so their ref_cnt exactly tracks the referencing requests.
        1.5. (Optional) For sliding window, skipped blocks are padded with nulls.
        2. Add the remaining computed blocks.

        Args:
            request_id: The request ID.
            new_computed_blocks: The new computed blocks just hitting the
                prefix cache.
            num_local_computed_tokens: The number of local computed tokens.
            num_external_computed_tokens: The number of external computed tokens.
        """
        # The coordinator only calls this for first-time allocations (running
        # requests are short-circuited there), so the request has no blocks yet.
        req_blocks = self.req_to_blocks[request_id]
        assert len(req_blocks) == 0
        num_total_computed_tokens = (
            num_local_computed_tokens + num_external_computed_tokens
        )
        num_skipped_tokens = self.get_num_skipped_tokens(num_total_computed_tokens)
        num_skipped_blocks = num_skipped_tokens // self.block_size
        if num_skipped_blocks > 0:
            # It is possible that all new computed blocks are skipped when
            # num_skipped_blocks > len(new_computed_blocks).
            new_computed_blocks = new_computed_blocks[num_skipped_blocks:]

        # Touch the computed blocks to make sure they won't be evicted.
        if self.enable_caching:
            self.block_pool.touch(new_computed_blocks)
        else:
            assert not any(new_computed_blocks), (
                "Computed blocks should be empty when prefix caching is disabled"
            )

        # Skip blocks are padded with null blocks.
        req_blocks.extend([self._null_block] * num_skipped_blocks)
        # Add the remaining computed blocks.
        req_blocks.extend(new_computed_blocks)
        # All cached hits (including skipped nulls) are already cached; mark
        # them so cache_blocks() will not try to re-cache blocks that already
        # have a block_hash set.
        self.num_cached_block[request_id] = len(req_blocks)
        if self._has_partial_local_hit(new_computed_blocks, num_local_computed_tokens):
            # Record the partial tail for the CoW redirect in
            # allocate_new_blocks; cap the cached count at the full blocks so
            # cache_blocks() re-caches the private copy once full.
            block_idx = num_local_computed_tokens // self.block_size
            self._partial_hit_reqs[request_id] = (block_idx, new_computed_blocks[-1])
            self.num_cached_block[request_id] = block_idx

    def allocate_external_computed_blocks(
        self,
        request_id: str,
        num_local_computed_tokens: int,
        num_external_computed_tokens: int,
    ) -> None:
        """
        Allocate new blocks for external (KV-connector) computed tokens.

        Must run only after every group's local blocks have been touched via
        `add_local_computed_blocks`, so this group's `get_new_blocks` cannot
        evict another group's cache-hit blocks (issue #33775).

        Args:
            request_id: The request ID.
            num_local_computed_tokens: The number of local computed tokens.
            num_external_computed_tokens: The number of external computed tokens.
        """
        num_total_computed_tokens = (
            num_local_computed_tokens + num_external_computed_tokens
        )
        num_skipped_tokens = self.get_num_skipped_tokens(num_total_computed_tokens)
        if num_skipped_tokens > 0:
            # Some external computed tokens may be skipped too.
            num_external_computed_tokens = min(
                num_total_computed_tokens - num_skipped_tokens,
                num_external_computed_tokens,
            )
        if num_external_computed_tokens <= 0:
            return

        req_blocks = self.req_to_blocks[request_id]
        allocated_blocks = self.block_pool.get_new_blocks(
            cdiv(num_total_computed_tokens, self.block_size) - len(req_blocks)
        )
        req_blocks.extend(allocated_blocks)
        if self._record_new_block_ids:
            self.new_block_ids.extend(b.block_id for b in allocated_blocks)

    def allocate_new_blocks(
        self, request_id: str, num_tokens: int, num_tokens_main_model: int
    ) -> list[KVCacheBlock]:
        """
        Allocate new blocks for the request to give it at least `num_tokens`
        token slots.

        Args:
            request_id: The request ID.
            num_tokens: The total number of tokens that need a slot (including
                tokens that are already allocated).
            num_tokens_main_model: The number of tokens for the main model (aka target
                model in spec decode). w/o spec decode, it is num_tokens;
                with spec decode, it is num_tokens - num_lookahead_tokens.
        Returns:
            The new allocated blocks.
        """
        cow_blocks: list[KVCacheBlock] = []
        if request_id in self._partial_hit_reqs:
            # Partial hit: redirect the shared tail to a private CoW block.
            # Replacing in place keeps the length-based allocation below
            # correct; the extra block was reserved by
            # get_num_blocks_to_allocate.
            block_idx, source_block = self._partial_hit_reqs.pop(request_id)
            cow_block = self.block_pool.get_new_blocks(1)[0]
            self._apply_cow(request_id, block_idx, source_block, cow_block)
            self.new_block_ids.append(cow_block.block_id)
            cow_blocks.append(cow_block)

        req_blocks = self.req_to_blocks[request_id]
        num_required_blocks = cdiv(num_tokens, self.block_size)
        num_new_blocks = num_required_blocks - len(req_blocks)
        if num_new_blocks <= 0:
            return cow_blocks
        else:
            new_blocks = self.block_pool.get_new_blocks(num_new_blocks)
            req_blocks.extend(new_blocks)
            if self._record_new_block_ids:
                self.new_block_ids.extend(b.block_id for b in new_blocks)
            return cow_blocks + new_blocks

    @property
    def records_new_block_ids(self) -> bool:
        """Whether this manager's new blocks are zeroed by the worker."""
        return self._record_new_block_ids

    def take_new_block_ids(self) -> list[int]:
        """Drain and return block IDs allocated since the last call."""
        ids = self.new_block_ids
        self.new_block_ids = []
        return ids

    def take_pending_cow_copies(
        self,
    ) -> list[tuple[KVCacheBlock, KVCacheBlock]]:
        """Drain pending CoW source and destination block pairs."""
        pending_copies = self._pending_cow_copies
        self._pending_cow_copies = []
        return pending_copies

    def take_pending_partial_tail_offloads(
        self,
    ) -> list[tuple[str, int, KVCacheBlock, int]]:
        """Drain producer partial-tail hand-offs.

        Entries are ``(req_id, group_id, block, boundary_tokens)``.

        Only mamba "align" populates this. The block lives off the request
        block table, so the caller must pin it until the connector has read
        it — nothing else keeps it alive once the CoW retention is released.
        """
        pending = self._pending_partial_tail_offloads
        self._pending_partial_tail_offloads = []
        return pending

    def _apply_cow(
        self,
        request_id: str,
        block_idx: int,
        source_block: KVCacheBlock,
        cow_block: KVCacheBlock,
    ) -> None:
        """Redirect a partial prefix-cache hit to a private CoW block.

        Both copy endpoints stay retained until the copy has run on the worker,
        so a same-step free cannot recycle them: ``source_block`` keeps its
        hit-ref, ``cow_block`` takes an extra ref beyond the one handed to the
        request.
        """
        req_blocks = self.req_to_blocks[request_id]
        assert block_idx < len(req_blocks)
        assert req_blocks[block_idx] is source_block
        assert not source_block.is_null and source_block.ref_cnt > 0
        req_blocks[block_idx] = cow_block
        self._pending_cow_copies.append((source_block, cow_block))
        cow_block.ref_cnt += 1

    def cache_blocks(
        self,
        request: Request,
        num_tokens: int,
        retention_interval: int | None = None,
    ) -> None:
        """
        Cache the blocks for the request.

        Args:
            request: The request.
            num_tokens: The total number of tokens that need to be cached
                (including tokens that are already cached).
            retention_interval: Sparse local-checkpoint granularity. ``None``
                keeps dense checkpointing; ``0`` keeps only the latest replay
                boundary; a positive multiple of ``scheduler_block_size`` keeps
                a tail once per that-sized segment. Only SWA acts on it.
        """
        num_cached_blocks = self.num_cached_block.get(request.request_id, 0)
        num_full_blocks = num_tokens // self.block_size

        if num_cached_blocks >= num_full_blocks:
            return

        # Token boundaries whose reachable tail must be retained under sparse
        # retention: the replay boundary (``num_prompt - 1``, capped by
        # ``get_computed_blocks``) and any detected shared-prefix junction.
        reachable_boundaries = [request.num_prompt_tokens - 1]
        if request.shared_prefix_boundary:
            reachable_boundaries.append(request.shared_prefix_boundary)

        block_mask = self.reachable_block_mask(
            start_block=num_cached_blocks,
            end_block=num_full_blocks,
            alignment_tokens=self.scheduler_block_size,
            kv_cache_spec=self.kv_cache_spec,
            use_eagle=self.use_eagle,
            retention_interval=retention_interval,
            reachable_boundaries=reachable_boundaries,
        )
        self.block_pool.cache_full_blocks(
            request=request,
            blocks=self.req_to_blocks[request.request_id],
            num_cached_blocks=num_cached_blocks,
            num_full_blocks=num_full_blocks,
            block_size=self.block_size,
            kv_cache_group_id=self.kv_cache_group_id,
            block_mask=block_mask,
        )

        self.num_cached_block[request.request_id] = num_full_blocks

    @classmethod
    def reachable_block_mask(
        cls,
        start_block: int,
        end_block: int,
        alignment_tokens: int | None,
        kv_cache_spec: KVCacheSpec,
        use_eagle: bool,
        retention_interval: int | None = None,
        reachable_boundaries: Sequence[int] = (),
    ) -> list[bool] | None:
        """Per-block mask for ``cache_full_blocks``. ``None`` means cache
        every (non-null) block — the default for full attention.

        Subclasses with sparse hit semantics (SWA / Mamba) override this to skip
        blocks that can never serve a hit at any alignment-aligned prefix length.
        ``reachable_boundaries`` are token positions whose reachable tail must be
        retained; the base (dense) policy ignores them.
        """
        return None

    def pop_blocks_for_free(self, request_id: str) -> list[KVCacheBlock]:
        """
        Pop the request's bookkeeping and return its blocks without yet
        returning them to the block pool. The caller is responsible for
        eventually passing the returned blocks to `block_pool.free_blocks`,
        freeing them in reverse order (so that tail blocks are evicted first).

        Args:
            request_id: The request ID.

        Returns:
            The request's blocks in allocation order.
        """
        # Default to [] in case a request is freed (aborted) before alloc.
        req_blocks = self.req_to_blocks.pop(request_id, [])
        self.num_cached_block.pop(request_id, None)
        self._partial_hit_reqs.pop(request_id, None)
        return req_blocks

    def free(self, request_id: str) -> None:
        """
        Free the blocks for the request.

        Args:
            request_id: The request ID.
        """
        # Free blocks in reverse order so that the tail blocks are freed first.
        self.block_pool.free_blocks(reversed(self.pop_blocks_for_free(request_id)))

    @abstractmethod
    def get_num_common_prefix_blocks(self, running_request_id: str) -> int:
        """
        Get the number of common prefix blocks for all requests with allocated
        KV cache.

        Args:
            running_request_id: The request ID.

        Returns:
            The number of common prefix blocks for all requests with allocated
            KV cache.
        """

        raise NotImplementedError

    @classmethod
    @abstractmethod
    def find_longest_cache_hit(
        cls,
        block_hashes: BlockHashList,
        max_length: int,
        kv_cache_group_ids: list[int],
        block_pool: BlockPool,
        kv_cache_spec: KVCacheSpec,
        drop_eagle_block: bool,
        alignment_tokens: int,
        dcp_world_size: int = 1,
        pcp_world_size: int = 1,
    ) -> tuple[tuple[list[KVCacheBlock], ...], int]:
        """
        Get the longest cache hit prefix of the blocks that is not longer than
        `max_length`. The prefix should be a common prefix hit for all the
        kv cache groups in `kv_cache_group_ids`. If no cache hit is found,
        return an empty list.
        If eagle is enabled, drop the last matched block to force recompute the
        last block to get the required hidden states for eagle drafting head.
        For multi-module MTP, this recompute also rewrites the dropped block's
        draft-layer KVs, which depend on up to num_speculative_tokens - 1
        tokens past the matched prefix (i.e. on the cache writer's
        continuation, which the block hash does not cover); the coordinator
        asserts the block size covers that window.
        Need to be customized for each attention type.

        Args:
            block_hashes: The block hashes of the request.
            max_length: The maximum length of the cache hit prefix.
            kv_cache_group_ids: The ids of the kv cache groups.
            block_pool: The block pool.
            kv_cache_spec: The kv cache spec.
            drop_eagle_block: Whether to drop the last matched block for EAGLE/MTP.
                Always False for non-EAGLE/MTP groups, but can be False for EAGLE/MTP
                groups too if the last block is already dropped (e.g., in a
                convergence loop in `find_longest_cache_hit`).
            alignment_tokens: The returned cache hit length (in tokens) should
                be a multiple of this value (in tokens). By default, it should
                be set to the block_size.
            dcp_world_size: The world size of decode context parallelism.
            pcp_world_size: The world size of prefill context parallelism.

        Returns:
            A tuple containing cached blocks and the exact cache-hit length in
            tokens. The cached block tuple has skipped blocks replaced by null
            blocks for each kv cache group in `kv_cache_group_ids`.
            For example, sliding window manager should return a list like
            ([NULL, NULL, KVCacheBlock(7), KVCacheBlock(8)]) for block size 4
            and sliding window 8 and len(kv_cache_group_ids) = 1.
        """

        raise NotImplementedError

    def _remove_blocks_in_range(
        self,
        request_id: str,
        first_block: int,
        last_block: int,
    ) -> None:
        """Free blocks in ``[first_block, last_block)`` and replace with null_block.

        Iterates backward so newly-evictable tail blocks are reached even after
        earlier blocks in the range were nulled in a prior call.
        """
        if request_id not in self.req_to_blocks:
            return
        if first_block >= last_block:
            return
        blocks = self.req_to_blocks[request_id]
        last_block = min(last_block, len(blocks))

        freed: list[KVCacheBlock] = []
        for i in range(last_block - 1, first_block - 1, -1):
            if blocks[i] == self._null_block:
                break
            freed.append(blocks[i])
            blocks[i] = self._null_block
        if freed:
            self.block_pool.free_blocks(freed)

    def remove_skipped_blocks(
        self,
        request_id: str,
        processed_computed_tokens: int,
        num_prompt_tokens: int | None = None,
    ) -> None:
        """
        Remove and free the blocks that are no longer needed for attention computation.
        The removed blocks should be replaced by null_block.

        This function depends on `get_num_skipped_tokens`, which need to be implemented
        differently for each attention type.

        Args:
            request_id: The request ID.
            processed_computed_tokens: Computed-token prefix length covering
                fully processed and committed tokens only (safe to free).
            num_prompt_tokens: Optional prompt length for attention types (e.g.
                R-SWA) that evict a middle gap rather than a head prefix. Ignored
                by the default implementation.
        """
        del num_prompt_tokens
        # Remove the blocks that will be skipped during attention computation.
        num_skipped_tokens = self.get_num_skipped_tokens(processed_computed_tokens)
        if num_skipped_tokens <= 0:
            # This indicates that ALL tokens are inside attention window.
            # Thus we do not need to free any blocks outside attention window.
            # A typical case is full attention that we never free any token
            # before the request is finished.
            return
        blocks = self.req_to_blocks[request_id]
        num_skipped_blocks = num_skipped_tokens // self.block_size
        # `num_skipped_tokens` may include tokens that haven't been allocated yet
        # (e.g., when the attention window moves into the external computed tokens
        # range), so we must cap to the number of blocks that currently exist for
        # this request.
        num_skipped_blocks = min(num_skipped_blocks, len(blocks))
        self._remove_blocks_in_range(request_id, 0, num_skipped_blocks)

    def get_num_skipped_tokens(self, num_computed_tokens: int) -> int:
        """
        Get the number of tokens that will be skipped for attention computation.

        Args:
            num_computed_tokens: The number of tokens that have been computed.

        Returns:
            The number of tokens that will be skipped for attention computation.
        """
        # The default behavior is to not skip any tokens.
        return 0

    def new_step_starts(self) -> None:
        return None


class FullAttentionManager(SingleTypeKVCacheManager):
    supports_fine_grained_hash_lookup: ClassVar[bool] = True

    @classmethod
    def find_longest_cache_hit(
        cls,
        block_hashes: BlockHashList,
        max_length: int,
        kv_cache_group_ids: list[int],
        block_pool: BlockPool,
        kv_cache_spec: KVCacheSpec,
        drop_eagle_block: bool,
        alignment_tokens: int,
        dcp_world_size: int = 1,
        pcp_world_size: int = 1,
    ) -> tuple[tuple[list[KVCacheBlock], ...], int]:
        assert isinstance(
            kv_cache_spec, FullAttentionSpec | ChunkedLocalAttentionSpec
        ), (
            "FullAttentionManager can only be used for full attention "
            "and chunked local attention groups"
        )
        block_size = kv_cache_spec.block_size
        if dcp_world_size > 1:
            # DCP shards each block's KV across ranks; hashes must be viewed at
            # the sharded block size.
            block_size *= dcp_world_size
        block_hashes = resolve_block_hashes(
            block_hashes,
            block_pool.hash_block_size,
            block_size,
            supports_fine_grained_hash_lookup=cls.supports_fine_grained_hash_lookup,
            alignment_tokens=alignment_tokens,
        )

        # Fine-grained mode (alignment_tokens == hash_block_size <
        # block_size): resolve_block_hashes kept the raw hash-granularity
        # list so interior boundaries can be probed.
        fine_grained = (
            alignment_tokens < block_size and block_size % alignment_tokens == 0
        )
        if fine_grained:
            # list or lazy BlobBlockHashes view
            assert isinstance(block_hashes, Sequence)
            full_block_hashes: BlockHashList = BlockHashListWithBlockSize(
                block_hashes, alignment_tokens, block_size
            )
        else:
            full_block_hashes = block_hashes

        computed_blocks: tuple[list[KVCacheBlock], ...] = tuple(
            [] for _ in range(len(kv_cache_group_ids))
        )
        # Phase 1: longest run of cached full blocks from the start. A missing
        # block implies every later block misses too (chained hashes).
        for block_hash in itertools.islice(full_block_hashes, max_length // block_size):
            cached_block = block_pool.get_cached_block(block_hash, kv_cache_group_ids)
            if not cached_block:
                break
            for computed, cached in zip(computed_blocks, cached_block):
                computed.append(cached)
        hit_length = len(computed_blocks[0]) * block_size

        # Phase 2 (fine-grained only): extend into the first non-full block by
        # probing its interior hash boundaries high-to-low (longest hit first).
        if fine_grained:
            # list or lazy BlobBlockHashes view
            assert isinstance(block_hashes, Sequence)
            scale_factor = block_size // alignment_tokens
            first_partial_idx = len(computed_blocks[0]) * scale_factor
            max_partial_idx = min(
                first_partial_idx + scale_factor - 1,
                max_length // alignment_tokens,
                len(block_hashes),
            )
            for fine_idx in range(max_partial_idx - 1, first_partial_idx - 1, -1):
                cached_tail = block_pool.get_cached_block(
                    block_hashes[fine_idx], kv_cache_group_ids
                )
                if not cached_tail:
                    continue
                for computed, cached in zip(computed_blocks, cached_tail):
                    computed.append(cached)
                hit_length = (fine_idx + 1) * alignment_tokens
                break

        # Eagle needs the tokens right before the generation point recomputed:
        # drop one hash unit when fine-grained (the tail block's KV is
        # append-only, so it still covers the reduced length), else one cache
        # block.
        if drop_eagle_block and hit_length > 0:
            hit_length -= min(alignment_tokens, block_size)
        # Round down to the alignment; a no-op when fine-grained (hits land on
        # hash boundaries by construction) and when alignment_tokens ==
        # block_size. Then trim blocks past the new tail.
        hit_length -= hit_length % alignment_tokens
        num_blocks = cdiv(hit_length, block_size)
        for computed in computed_blocks:
            del computed[num_blocks:]
        return computed_blocks, hit_length

    def cache_blocks(
        self,
        request: Request,
        num_tokens: int,
        retention_interval: int | None = None,
    ) -> None:
        super().cache_blocks(request, num_tokens, retention_interval=retention_interval)
        hash_block_size = self.block_pool.hash_block_size
        if self.block_size == hash_block_size:
            return
        self._cache_partial_tail_block(request, num_tokens)

    def _cache_partial_tail_block(
        self,
        request: Request,
        num_tokens: int,
    ) -> None:
        """Cache the prompt tail when it ends inside a cache block.

        Only the final prompt hash boundary is registered as a partial
        prefix-cache entry; intermediate hash boundaries inside the same cache
        block are intentionally skipped.
        """
        hash_block_size = self.block_pool.hash_block_size
        boundary_tokens = request.num_prompt_tokens // hash_block_size * hash_block_size
        if boundary_tokens == 0 or boundary_tokens > num_tokens:
            return
        if boundary_tokens % self.block_size == 0:
            return

        blocks = self.req_to_blocks[request.request_id]
        block_idx = boundary_tokens // self.block_size
        if block_idx >= len(blocks):
            return
        self.block_pool.cache_partial_block(
            request=request,
            block=blocks[block_idx],
            num_tokens=boundary_tokens,
            kv_cache_group_id=self.kv_cache_group_id,
            block_size=self.block_size,
        )

    def get_num_common_prefix_blocks(self, running_request_id: str) -> int:
        with perfmark.region("vllm-040"):
            blocks = self.req_to_blocks[running_request_id]
            num_common_blocks = 0
            for block in blocks:
                if block.ref_cnt == len(self.req_to_blocks):
                    num_common_blocks += 1
                else:
                    break
            return num_common_blocks


class RSWAManager(FullAttentionManager):
    """KV cache manager for Reference Sliding Window Attention (R-SWA).

    When ``num_prompt_tokens`` is supplied to ``remove_skipped_blocks``, frees
    gap blocks between the prefill tail and the current decode window.  This
    bounds per-request KV memory at O(prefix_len + rswa_window) instead of
    growing linearly with decode length.
    """

    def __init__(self, kv_cache_spec: RSWASpec, **kwargs) -> None:
        super().__init__(kv_cache_spec, **kwargs)
        self.rswa_window: int = kv_cache_spec.rswa_window

    def remove_skipped_blocks(
        self,
        request_id: str,
        processed_computed_tokens: int,
        num_prompt_tokens: int | None = None,
    ) -> None:
        """Free gap blocks that are no longer needed for attention.

        Gap = blocks entirely within
            [ceil(prefix_len / block_size) * block_size,
             max(prefix_len, processed_computed_tokens - rswa_window))

        Freed blocks are replaced with null_block in req_to_blocks so the
        block_table passed to FA4 is valid (null_block KV is all-zero;
        rswa_mask_mod marks gap positions as non-visible so FA4 skips them).
        """
        if num_prompt_tokens is None:
            super().remove_skipped_blocks(
                request_id, processed_computed_tokens, num_prompt_tokens
            )
            return

        bs = self.block_size
        # First block fully after the prefill boundary.
        first_gap_block = cdiv(num_prompt_tokens, bs)
        # Decode window start position; blocks before this are evictable.
        window_start = max(
            num_prompt_tokens, processed_computed_tokens - self.rswa_window
        )
        last_gap_block = window_start // bs  # exclusive upper bound
        self._remove_blocks_in_range(request_id, first_gap_block, last_gap_block)


class SlidingWindowManager(SingleTypeKVCacheManager):
    def __init__(self, kv_cache_spec: SlidingWindowSpec, **kwargs) -> None:
        super().__init__(kv_cache_spec, **kwargs)
        self.sliding_window = kv_cache_spec.sliding_window
        # Extra trailing tokens to retain below the window (never attended) so a
        # multi-module MTP store-side lag can still reconstruct the window from
        # cached blocks.
        self.extra_retained_tokens = kv_cache_spec.extra_retained_tokens

    @classmethod
    def _contiguous_blocks_for_hit(
        cls, window_size: int, block_size: int, use_eagle: bool
    ) -> int:
        blocks = cdiv(window_size - 1, block_size)
        if use_eagle:
            # Need to drop the last matched block if eagle is enabled. For
            # sliding window layer, we achieve this by increasing the number of
            # contiguous blocks needed for prefix cache hit by one and dropping
            # the last matched block.
            blocks += 1
        return blocks

    @classmethod
    def find_longest_cache_hit(
        cls,
        block_hashes: BlockHashList,
        max_length: int,
        kv_cache_group_ids: list[int],
        block_pool: BlockPool,
        kv_cache_spec: KVCacheSpec,
        drop_eagle_block: bool,
        alignment_tokens: int,
        dcp_world_size: int = 1,
        pcp_world_size: int = 1,
    ) -> tuple[tuple[list[KVCacheBlock], ...], int]:
        assert isinstance(kv_cache_spec, SlidingWindowSpec), (
            "SlidingWindowManager can only be used for sliding window groups"
        )
        assert dcp_world_size == 1, "DCP not support sliding window attn now."
        assert pcp_world_size == 1, "PCP not support sliding window attn now."
        # Fine-grained partial hits are not supported for sliding window now
        assert alignment_tokens % kv_cache_spec.block_size == 0, (
            "SlidingWindowManager does not support fine-grained (partial) cache hits"
        )
        block_hashes = resolve_block_hashes(
            block_hashes,
            block_pool.hash_block_size,
            kv_cache_spec.block_size,
            supports_fine_grained_hash_lookup=cls.supports_fine_grained_hash_lookup,
            alignment_tokens=alignment_tokens,
        )

        # The number of contiguous blocks needed for a prefix cache hit.
        sliding_window_contiguous_blocks = cls._contiguous_blocks_for_hit(
            kv_cache_spec.sliding_window, kv_cache_spec.block_size, drop_eagle_block
        )

        # TODO: reduce i by sliding_window_contiguous_blocks when cache miss, to
        # optimize the time complexity from O(max_num_blocks) to
        # O(max_num_blocks / sliding_window_contiguous_blocks +
        # sliding_window_contiguous_blocks),
        # which is good for low cache hit rate scenarios.
        max_num_blocks = max_length // kv_cache_spec.block_size
        computed_blocks: tuple[list[KVCacheBlock], ...] = tuple(
            [block_pool.null_block] * max_num_blocks
            for _ in range(len(kv_cache_group_ids))
        )
        block_size = kv_cache_spec.block_size
        num_contiguous_blocks = 0
        match_found = False
        # Search from right to left and early stop when a match is found.
        for i in range(max_num_blocks - 1, -1, -1):
            if cached_block := block_pool.get_cached_block(
                block_hashes[i], kv_cache_group_ids
            ):
                # Skip prefix matching check if the block is not aligned with
                # `alignment_tokens`.
                if num_contiguous_blocks == 0 and block_size != alignment_tokens:
                    post_pop_blocks = i if drop_eagle_block else i + 1
                    if (post_pop_blocks * block_size) % alignment_tokens != 0:
                        continue
                # Add the cached block to the computed blocks.
                for computed, cached in zip(computed_blocks, cached_block):
                    computed[i] = cached
                num_contiguous_blocks += 1
                if num_contiguous_blocks >= sliding_window_contiguous_blocks:
                    # Trim the trailing blocks.
                    # E.g., [NULL, NULL, 8, 3, NULL, 9] -> [NULL, NULL, 8, 3]
                    # when sliding_window_contiguous_blocks=2.
                    for computed in computed_blocks:
                        del computed[i + num_contiguous_blocks :]
                    match_found = True
                    break
            else:
                num_contiguous_blocks = 0
        if not match_found:
            # The first `num_contiguous_blocks` is a cache hit even if
            # `num_contiguous_blocks < sliding_window_contiguous_blocks`.
            for computed in computed_blocks:
                del computed[num_contiguous_blocks:]
            while (
                block_size != alignment_tokens  # Faster for common case.
                and len(computed_blocks[0]) * block_size % alignment_tokens != 0
            ):
                for computed in computed_blocks:
                    computed.pop()
        if drop_eagle_block and computed_blocks[0]:
            for computed in computed_blocks:
                computed.pop()
            # Re-align after eagle pop: the pop may break the alignment
            # when block_size != alignment_tokens (hybrid models with
            # different page sizes, e.g. Gemma4).
            while (
                block_size != alignment_tokens
                and len(computed_blocks[0]) * block_size % alignment_tokens != 0
            ):
                for computed in computed_blocks:
                    computed.pop()
        hit_length = len(computed_blocks[0]) * block_size
        return computed_blocks, hit_length

    @classmethod
    def reachable_block_mask(
        cls,
        start_block: int,
        end_block: int,
        alignment_tokens: int | None,
        kv_cache_spec: KVCacheSpec,
        use_eagle: bool,
        retention_interval: int | None = None,
        reachable_boundaries: Sequence[int] = (),
    ) -> list[bool] | None:
        assert isinstance(kv_cache_spec, SlidingWindowSpec)
        if alignment_tokens is None:
            # Fast path: when the coordinator imposes no alignment constraint.
            return None
        assert alignment_tokens % kv_cache_spec.block_size == 0

        block_size = kv_cache_spec.block_size
        # Contiguous blocks a hit needs at a boundary (incl. the EAGLE peek).
        need = cls._contiguous_blocks_for_hit(
            window_size=kv_cache_spec.sliding_window,
            block_size=block_size,
            use_eagle=use_eagle,
        )
        # The matched run's right edge sits on the aligned boundary block when
        # EAGLE peeks one block past it (shift=1), otherwise on the last block
        # before the boundary (shift=0).
        shift = 1 if use_eagle else 0

        mask = [False] * (end_block - start_block)

        # (1) Segment-boundary tails. ``retention_interval``:
        #   None -> dense (a tail at every ``alignment_tokens`` boundary);
        #   0    -> no dense tails (only the replay boundary below);
        #   >0   -> a tail once per ``retention_interval``-sized segment.
        segment_tokens = (
            alignment_tokens
            if retention_interval is None
            else (None if retention_interval == 0 else retention_interval)
        )
        if segment_tokens is not None:
            per_segment = segment_tokens // block_size
            if need >= per_segment:
                # Every block is reachable; cache them all.
                return None
            for i in range(start_block, end_block):
                if i >= shift and (i - shift) % per_segment >= per_segment - need:
                    mask[i - start_block] = True

        # (2) Reachable-boundary tails: the replay boundary (``num_prompt - 1``,
        # capped by ``get_computed_blocks``) and any shared-prefix junction. Both
        # land before segments would cover them under sparse retention, so keep
        # the ``need``-block tail ending on each boundary explicitly.
        if retention_interval is not None:
            for boundary_tokens in reachable_boundaries:
                aligned = boundary_tokens // alignment_tokens * alignment_tokens
                end = aligned // block_size + shift
                for j in range(max(start_block, end - need), min(end_block, end)):
                    mask[j - start_block] = True

        return mask

    def get_num_skipped_tokens(self, num_computed_tokens: int) -> int:
        """
        Get the number of tokens that will be skipped for attention computation.

        For sliding window, this corresponds to the tokens that are prior to
        the current sliding window.

        Example:
        sliding_window=4, num_computed_tokens=7

        Tokens:   [ 0  1  2  3  4  5  6  7 ]
                  | ---- computed -----|
                                         ^ next token to be computed
                               |-----------| sliding window for next token
                  |--skipped---|

        The current window contains tokens 4~7. Tokens 0~3 will be skipped for
        attention computation since they are outside the sliding window.
        Thus, get_num_skipped_tokens(7) == 4.

        The trailing edge of the window is extended by ``extra_retained_tokens``
        so that those extra trailing tokens' blocks are retained (but not
        attended). This is needed for multi-module spec decoding which can
        re-prefill the last num_spec_prefill_tokens - 1 tokens from the end
        of the sequence, and thus needs to delay freeing/caching of blocks.

        Args:
            num_computed_tokens: The number of tokens that have been computed.

        Returns:
            The number of tokens that will be skipped for attention computation.
        """
        return max(
            0,
            num_computed_tokens - self.sliding_window + 1 - self.extra_retained_tokens,
        )

    def get_num_common_prefix_blocks(self, running_request_id: str) -> int:
        """
        NOTE(Chen): The prefix blocks are null blocks for sliding window layers.
        So it's not correct to count ref_cnt like FullAttentionManager. Return
        0 here for correctness. Need to support cascade attention + sliding
        window in the future.
        """
        return 0


class ChunkedLocalAttentionManager(SingleTypeKVCacheManager):
    def __init__(self, kv_cache_spec: ChunkedLocalAttentionSpec, **kwargs) -> None:
        super().__init__(kv_cache_spec, **kwargs)
        self.attention_chunk_size = kv_cache_spec.attention_chunk_size

    @classmethod
    def find_longest_cache_hit(
        cls,
        block_hashes: BlockHashList,
        max_length: int,
        kv_cache_group_ids: list[int],
        block_pool: BlockPool,
        kv_cache_spec: KVCacheSpec,
        drop_eagle_block: bool,
        alignment_tokens: int,
        dcp_world_size: int = 1,
        pcp_world_size: int = 1,
    ) -> tuple[tuple[list[KVCacheBlock], ...], int]:
        """
        For chunked local attention, we need to find the longest cache hit
        prefix of the blocks that is not longer than `max_length`. The prefix
        should be a common prefix hit for all the kv cache groups in
        `kv_cache_group_ids`. If no cache hit is found, return an empty list.
        note we mark as computed if the whole block is outside of the local
        window, and set the block as null. Examples:

        1. Attention chunk size of 8, block size of 4, max length of 15
        for next token at 15th (zero-indexed), 8th - 14th tokens are in
        the window(needs lookup), 0th - 7th are not in the window,
        so they are already marked as computed. We check the complete
        block3 (8th - 11th tokens), Assume block 3 is hit, we will return
        [null, null, block 3], otherwise, we return [null, null]

        2. Attention chunk size of 8, block size of 4, max length of 16
        for next token at 16th (zero-indexed), 0th - 15th tokens are not
        in the window, so they are already marked as computed.
        we return 4 blocks[null, null, null, null]

        Args:
            block_hashes: The block hashes of the request.
            max_length: The maximum length of the cache hit prefix.
            kv_cache_group_ids: The ids of the kv cache groups.
            block_pool: The block pool.
            kv_cache_spec: The kv cache spec.
            drop_eagle_block: Whether to drop the last matched block for EAGLE/MTP.
            dcp_world_size: The world size of decode context parallelism.
            pcp_world_size: The world size of prefill context parallelism.
            alignment_tokens: The returned cache hit length (in tokens) should
                be a multiple of this value (in tokens).

        Returns:
            A list of cached blocks
        """
        assert isinstance(kv_cache_spec, ChunkedLocalAttentionSpec), (
            "ChunkedLocalAttentionManager can only be used for "
            "chunked local attention groups"
        )
        assert drop_eagle_block is False, (
            "Hybrid KV cache is not supported for " + "eagle + chunked local attention."
        )
        assert dcp_world_size == 1, "DCP not support chunked local attn now."
        assert pcp_world_size == 1, "PCP not support chunked local attn now."
        assert kv_cache_spec.block_size == alignment_tokens, (
            "KV cache groups with different block sizes are not compatible with "
            "chunked local attention now"
        )
        block_hashes = resolve_block_hashes(
            block_hashes,
            block_pool.hash_block_size,
            kv_cache_spec.block_size,
            supports_fine_grained_hash_lookup=cls.supports_fine_grained_hash_lookup,
            alignment_tokens=alignment_tokens,
        )
        max_num_blocks = max_length // kv_cache_spec.block_size
        if max_length > 0:
            local_attention_start_idx = (
                max_length
                // kv_cache_spec.attention_chunk_size
                * kv_cache_spec.attention_chunk_size
            )
        else:
            local_attention_start_idx = 0
        # we marked blocks out of window as computed
        # with null blocks, and blocks inside window based on cache lookup
        # result [null] [null] ... [null] [hit block 1 (1st block contain
        # last window)] [hit block 2] ... [hit block x]
        local_attention_start_block_idx = (
            local_attention_start_idx // kv_cache_spec.block_size
        )
        computed_blocks: tuple[list[KVCacheBlock], ...] = tuple(
            [block_pool.null_block] * local_attention_start_block_idx
            for _ in range(len(kv_cache_group_ids))
        )
        for i in range(local_attention_start_block_idx, max_num_blocks):
            block_hash = block_hashes[i]
            if cached_block := block_pool.get_cached_block(
                block_hash, kv_cache_group_ids
            ):
                for computed, cached in zip(computed_blocks, cached_block):
                    computed.append(cached)
            else:
                break
        hit_length = len(computed_blocks[0]) * kv_cache_spec.block_size
        return computed_blocks, hit_length

    def get_num_skipped_tokens(self, num_computed_tokens: int) -> int:
        """
        Get the number of tokens that will be skipped for attention computation.

        For chunked local attention, this corresponds to the tokens that are on
        the left side of the current chunk.

        Example 1:
        chunk size = 8, num_computed_tokens = 13
        Tokens:  [ 0 1 2 3 4 5 6 7 | 8 9 10 11 12 13 14 15 ] ...
                 | ----- computed ---------------|
                                                  ^^ next token to be computed
                                   |----------------| <-- attention window for
                                                          next token
                 |--- skipped -----|
        Output: get_num_skipped_tokens(13) == 8

        Example 2:
        chunk size = 8, num_computed_tokens = 8
        Tokens:  [ 0 1 2 3 4 5 6 7 | 8 9 10 11 12 13 14 15 ] ...
                 | --- computed ---|
                                     ^ next token to be computed
                                   |--| <-- attention window for next token
                 | --- skipped ----|
        Output: get_num_skipped_tokens(8) == 8

        Example 3:
        chunk size = 8, num_computed_tokens = 7
        Tokens:  [ 0 1 2 3 4 5 6 7 | 8 9 10 11 12 13 14 15 ] ...
                 |---computed---|
                                 ^ next token to be computed
                 |-----------------| <-- attention window for next token
                 no token should be skipped.
        Output: get_num_skipped_tokens(7) == 0

        Args:
            num_computed_tokens: The number of tokens that have been computed.

        Returns:
            The number of tokens that will be skipped for attention computation.
        """
        num_skipped_tokens = (
            num_computed_tokens // self.attention_chunk_size
        ) * self.attention_chunk_size
        return num_skipped_tokens

    def get_num_common_prefix_blocks(self, running_request_id: str) -> int:
        """
        cascade attention is not supported by chunked local attention.
        """
        return 0


class MambaManager(SingleTypeKVCacheManager):
    supports_fine_grained_hash_lookup: ClassVar[bool] = True

    def __init__(
        self, kv_cache_spec: MambaSpec, block_pool: BlockPool, **kwargs
    ) -> None:
        super().__init__(kv_cache_spec, block_pool, **kwargs)
        # Mamba layers use TP instead of DCP, so each rank holds the full
        # recurrent state. Undo the DCP/PCP block_size scaling that the base
        # class applies for attention groups whose KV cache is partitioned.
        self.block_size = kv_cache_spec.block_size
        self.mamba_cache_mode = kv_cache_spec.mamba_cache_mode
        self.num_speculative_blocks: int = kv_cache_spec.num_speculative_blocks
        self.cached_blocks_this_step: set[BlockHashWithGroupId] = set()
        if self.mamba_cache_mode == "align":
            # Mapping from request ID to the index of the block
            # allocated in the previous step
            self.last_state_block_idx: dict[str, int] = {}
            # The set of the requests that have been allocated blocks
            self._allocated_block_reqs: set[str] = set()
            # Requests that registered their own last-prompt-boundary partial
            # tail (producers). On the next step's CoW the boundary state moves
            # into a private cow_block; we record that block for connector
            # offload (see _pending_partial_tail_offloads).
            self._producer_partial_tail_reqs: dict[str, int] = {}

    @classmethod
    def find_longest_cache_hit(
        cls,
        block_hashes: BlockHashList,
        max_length: int,
        kv_cache_group_ids: list[int],
        block_pool: BlockPool,
        kv_cache_spec: KVCacheSpec,
        drop_eagle_block: bool,
        alignment_tokens: int,
        dcp_world_size: int = 1,
        pcp_world_size: int = 1,
    ) -> tuple[tuple[list[KVCacheBlock], ...], int]:
        assert isinstance(kv_cache_spec, MambaSpec), (
            "MambaManager can only be used for mamba groups"
        )
        assert dcp_world_size == 1, "DCP not support mamba now."
        assert pcp_world_size == 1, "PCP not support mamba now."
        block_hashes = resolve_block_hashes(
            block_hashes,
            block_pool.hash_block_size,
            kv_cache_spec.block_size,
            supports_fine_grained_hash_lookup=cls.supports_fine_grained_hash_lookup,
            alignment_tokens=alignment_tokens,
        )
        computed_blocks: tuple[list[KVCacheBlock], ...] = tuple(
            [] for _ in range(len(kv_cache_group_ids))
        )
        hit_length = 0

        block_size = kv_cache_spec.block_size
        if alignment_tokens < block_size and block_size % alignment_tokens == 0:
            # list or lazy BlobBlockHashes view
            assert isinstance(block_hashes, Sequence)
            hash_block_size = alignment_tokens
            scale_factor = block_size // hash_block_size
            max_num_partial_units = min(
                max_length // hash_block_size, len(block_hashes)
            )
            for fine_idx in range(max_num_partial_units - 1, -1, -1):
                num_tokens = (fine_idx + 1) * hash_block_size
                block_hash = block_hashes[fine_idx]
                if cached_block := block_pool.get_cached_block(
                    block_hash, kv_cache_group_ids
                ):
                    block_idx = fine_idx // scale_factor
                    for computed, cached in zip(computed_blocks, cached_block):
                        computed.extend([block_pool.null_block] * block_idx)
                        computed.append(cached)
                    hit_length = num_tokens
                    break
            return computed_blocks, hit_length

        max_num_blocks = max_length // block_size
        # Search from right to left and early stop when a match is found.
        for i in range(max_num_blocks - 1, -1, -1):
            if cached_block := block_pool.get_cached_block(
                block_hashes[i], kv_cache_group_ids
            ):
                # When enable Mamba prefix caching, `block_size` will be aligned
                # across full attention layers and Mamba layers to ensure the
                # prefix hit length aligned at block
                if (
                    block_size != alignment_tokens  # Faster for common case.
                    and (i + 1) * block_size % alignment_tokens != 0
                ):
                    continue
                for computed, cached in zip(computed_blocks, cached_block):
                    # the hit length logic later assumes:
                    #  hit_length = len(hit_blocks_other_attn[0])
                    #               * self.other_block_size
                    # so we insert dummy blocks at the beginning:
                    computed.extend([block_pool.null_block] * i)
                    computed.append(cached)
                hit_length = (i + 1) * block_size
                break  # we just need the last match - early stopping

        return computed_blocks, hit_length

    @classmethod
    def reachable_block_mask(
        cls,
        start_block: int,
        end_block: int,
        alignment_tokens: int | None,
        kv_cache_spec: KVCacheSpec,
        use_eagle: bool,
        retention_interval: int | None = None,
        reachable_boundaries: Sequence[int] = (),
    ) -> list[bool] | None:
        """Sparse Mamba state-snapshot retention.

        ``retention_interval``:

          ``None`` -> dense (cache every block; default, unchanged behavior)
          ``0``    -> keep only the ``reachable_boundaries`` states
          ``> 0``  -> keep one state per ``retention_interval``-sized segment

        ``reachable_boundaries`` are proven reuse points (the replay boundary and
        any cross-request shared-prefix junction, Marconi-style APC); their
        boundary state is always kept so sparse retention does not defeat reuse.
        """
        if retention_interval is None or alignment_tokens is None:
            # Dense caching (default) or no alignment constraint imposed.
            return None
        assert isinstance(kv_cache_spec, MambaSpec)
        block_size = kv_cache_spec.block_size
        mask = [False] * (end_block - start_block)

        # (1) Segment-boundary states. A Mamba hit needs exactly the single
        # state block ending on the boundary (no window, and draft models have
        # no mamba layers, so no eagle shift). Block ``i`` ends at token
        # ``(i + 1) * block_size``.
        segment_tokens = None if retention_interval == 0 else retention_interval
        if segment_tokens is not None:
            per_segment = segment_tokens // block_size
            if per_segment <= 1:
                # Interval at/below the block size: every block is a boundary.
                return None
            first_boundary = (
                start_block + per_segment
            ) // per_segment * per_segment - 1
            for i in range(first_boundary - start_block, len(mask), per_segment):
                mask[i] = True

        # (2) Reachable-boundary states: the replay boundary (``num_prompt - 1``,
        # capped by ``get_computed_blocks``) and any shared-prefix junction, both
        # of which segments would otherwise skip under sparse retention. A Mamba
        # hit needs exactly the single state block ending on the boundary.
        for boundary_tokens in reachable_boundaries:
            aligned = boundary_tokens // alignment_tokens * alignment_tokens
            boundary_block = aligned // block_size - 1
            if start_block <= boundary_block < end_block:
                mask[boundary_block - start_block] = True

        return mask

    def remove_skipped_blocks(
        self,
        request_id: str,
        processed_computed_tokens: int,
        num_prompt_tokens: int | None = None,
    ) -> None:
        assert isinstance(self.kv_cache_spec, MambaSpec)

        super().remove_skipped_blocks(
            request_id, processed_computed_tokens, num_prompt_tokens
        )
        if self.mamba_cache_mode == "align":
            # `last_state_block_idx` refers to the block index allocated two steps ago.
            # The block allocated in the previous step is used to copy Mamba states
            # into the block allocated in the current step; the earlier block is
            # no longer needed and should be freed here.
            last_state_block_idx = self.last_state_block_idx.get(request_id)
            # Blocks allocated during prefill may be non-contiguous. Use
            # `last_state_block_idx` to free the appropriate block and replace it
            # with a null block.
            if (
                last_state_block_idx is not None
                and last_state_block_idx
                < cdiv(processed_computed_tokens, self.block_size) - 1
            ):
                blocks = self.req_to_blocks[request_id]
                if blocks[last_state_block_idx] != self._null_block:
                    self.block_pool.free_blocks([blocks[last_state_block_idx]])
                    blocks[last_state_block_idx] = self._null_block

    def get_num_common_prefix_blocks(self, running_request_id: str) -> int:
        """
        cascade attention is not supported by mamba
        """
        return 0

    def get_num_blocks_to_allocate(
        self,
        request_id: str,
        num_tokens: int,
        new_computed_blocks: Sequence[KVCacheBlock],
        total_computed_tokens: int,
        num_local_computed_tokens: int,
        num_tokens_main_model: int,
        apply_admission_cap: bool = False,
    ) -> int:
        assert isinstance(self.kv_cache_spec, MambaSpec)
        if (
            len(new_computed_blocks) > 0
            and new_computed_blocks[-1].block_hash in self.cached_blocks_this_step
        ):
            # Mamba can't rely on blocks generated by other requests in the current step
            # To put it in the next step, we return num_gpu_blocks + 1 so
            # that kv_cache_manager will think there is no enough blocks to allocate now
            # and don't schedule it in the current step.
            return self.block_pool.num_gpu_blocks + 1
        if self.mamba_cache_mode != "align":
            # Allocate extra `num_speculative_blocks` blocks for
            # speculative decoding (MTP/EAGLE) with linear attention.
            if self.num_speculative_blocks > 0:
                num_tokens += (
                    self.kv_cache_spec.block_size * self.num_speculative_blocks
                )
            return super().get_num_blocks_to_allocate(
                request_id,
                num_tokens,
                new_computed_blocks,
                total_computed_tokens,
                num_local_computed_tokens,
                num_tokens_main_model,
                apply_admission_cap=apply_admission_cap,
            )
        else:
            # We don't allocate blocks for lookahead tokens in align mode, because if
            # x * block_size tokens are scheduled, num_tokens is
            # x * block_size + num_lookahead_tokens and breaks the alignment.
            # We can ignore lookahead tokens because current draft models don't have
            # mamba layers.
            num_tokens = num_tokens_main_model

            # NOTE(tdouble): this is an over-estimate of how many blocks we need because
            # num_tokens can include draft tokens that will later be rejected.
            num_required_blocks = (
                cdiv(num_tokens, self.block_size) + self.num_speculative_blocks
            )
            num_new_blocks = (
                num_required_blocks
                - len(new_computed_blocks)
                - len(self.req_to_blocks[request_id])
            )
            has_partial_hit = (
                self._has_partial_local_hit(
                    new_computed_blocks, num_local_computed_tokens
                )
                or request_id in self._partial_hit_reqs
            )
            if has_partial_hit:
                num_new_blocks = max(num_new_blocks, 0) + 1
            if num_new_blocks > 0:
                if request_id in self._allocated_block_reqs:
                    # Old request. Needs at most 1 more blocks as we can reuse the
                    # speculative blocks in previous step.
                    num_new_blocks = 1 + int(has_partial_hit)
                else:
                    # First prefill. Allocate 1 block for running state, the
                    # speculative blocks, and one extra block if a partial cache
                    # hit must be copy-on-written before the new tokens run.
                    num_new_blocks = (
                        1 + self.num_speculative_blocks + int(has_partial_hit)
                    )

            num_evictable_computed_blocks = self._get_num_evictable_blocks(
                new_computed_blocks
            )
            return num_new_blocks + num_evictable_computed_blocks

    def allocate_new_blocks(
        self, request_id: str, num_tokens: int, num_tokens_main_model: int
    ) -> list[KVCacheBlock]:
        assert isinstance(self.kv_cache_spec, MambaSpec)
        if self.mamba_cache_mode != "align":
            # Allocate extra `num_speculative_blocks` blocks for
            # speculative decoding (MTP/EAGLE) with linear attention.
            if self.num_speculative_blocks > 0:
                num_tokens += self.block_size * self.num_speculative_blocks
            return super().allocate_new_blocks(
                request_id, num_tokens, num_tokens_main_model
            )
        else:
            # We don't allocate blocks for lookahead tokens in align mode, because if
            # x * block_size tokens are scheduled, num_tokens is
            # x * block_size + num_lookahead_tokens and breaks the alignment.
            # We can ignore lookahead tokens because current draft models don't have
            # mamba layers.
            num_tokens = num_tokens_main_model
            req_blocks: list[KVCacheBlock] = self.req_to_blocks[request_id]
            # NOTE(tdouble): this is an over-estimate of how many blocks we need because
            # num_tokens can include draft tokens that will later be rejected.
            num_required_blocks = (
                cdiv(num_tokens, self.block_size) + self.num_speculative_blocks
            )
            partial_hit = self._partial_hit_reqs.get(request_id)
            has_partial_hit = partial_hit is not None
            # `num_required_blocks` might be less than `len(req_blocks)` if blocks are
            # over-allocated at last round.
            if num_required_blocks <= len(req_blocks) and not has_partial_hit:
                self._allocated_block_reqs.add(request_id)
                return []
            else:
                prev_block_len = len(req_blocks)
                blocks_allocated = request_id in self._allocated_block_reqs
                # Record the last state block
                if blocks_allocated:
                    # We always save the running state at the last
                    # (1 + num_speculative_blocks) block
                    self.last_state_block_idx[request_id] = (
                        prev_block_len - 1 - self.num_speculative_blocks
                    )
                elif prev_block_len > 0:
                    # When a new request hits the prefix cache, the last block
                    # saves the hit state.
                    self.last_state_block_idx[request_id] = prev_block_len - 1

                num_skipped_blocks = (
                    num_required_blocks - self.num_speculative_blocks - 1
                )
                # null blocks
                if prev_block_len < num_skipped_blocks:
                    req_blocks.extend(
                        [
                            self._null_block
                            for _ in range(prev_block_len, num_skipped_blocks)
                        ]
                    )

                if blocks_allocated:
                    # reuse previous speculative blocks in this step
                    for block_idx in range(
                        prev_block_len - self.num_speculative_blocks, prev_block_len
                    ):
                        if block_idx < num_skipped_blocks:
                            req_blocks.append(req_blocks[block_idx])
                            req_blocks[block_idx] = self._null_block
                        else:
                            break
                num_new_blocks = num_required_blocks - len(req_blocks)
                if has_partial_hit:
                    num_new_blocks = max(num_new_blocks, 0) + 1
                if blocks_allocated:
                    assert num_new_blocks <= 1 + int(has_partial_hit)
                else:
                    assert num_new_blocks <= self.num_speculative_blocks + 1 + int(
                        has_partial_hit
                    )
                new_blocks = self.block_pool.get_new_blocks(num_new_blocks)
                returned_blocks = req_blocks[prev_block_len:]
                if partial_hit is not None:
                    block_idx, source_block = partial_hit
                    cow_block = new_blocks[0]
                    new_blocks = new_blocks[1:]
                    if blocks_allocated:
                        # The worker block table of a running request is
                        # append-only, so the request must stay on
                        # source_block. Move the cache entry to cow_block
                        # instead; the queued copy fills it before forward
                        # overwrites source_block.
                        assert req_blocks[block_idx] is source_block
                        self.block_pool.move_block_hashes(source_block, cow_block)
                        self._pending_cow_copies.append((source_block, cow_block))
                        source_block.ref_cnt += 1
                        boundary_tokens = self._producer_partial_tail_reqs.pop(
                            request_id, None
                        )
                        if boundary_tokens is not None:
                            # This CoW preserved a producer's own boundary
                            # state in cow_block; hand it to the connector for
                            # partial-tail offload once the copy has run.
                            self._pending_partial_tail_offloads.append(
                                (
                                    request_id,
                                    self.kv_cache_group_id,
                                    cow_block,
                                    boundary_tokens,
                                )
                            )
                        if cow_block.block_hash is not None:
                            # The moved entry is only filled by this step's
                            # copy, so defer same-step hits on it.
                            self.cached_blocks_this_step.add(cow_block.block_hash)
                    else:
                        self._apply_cow(request_id, block_idx, source_block, cow_block)
                        returned_blocks = [cow_block] + returned_blocks
                req_blocks.extend(new_blocks)
                self._allocated_block_reqs.add(request_id)
                self._partial_hit_reqs.pop(request_id, None)
                returned_blocks.extend(new_blocks)
                return returned_blocks

    def pop_blocks_for_free(self, request_id: str) -> list[KVCacheBlock]:
        if self.mamba_cache_mode == "align":
            self._allocated_block_reqs.discard(request_id)
            self.last_state_block_idx.pop(request_id, None)
            self._producer_partial_tail_reqs.pop(request_id, None)
            # A hand-off whose request died in this same scheduling pass must
            # not reach the connector: its unpin hook (free) has already run.
            self._pending_partial_tail_offloads = [
                entry
                for entry in self._pending_partial_tail_offloads
                if entry[0] != request_id
            ]
        return super().pop_blocks_for_free(request_id)

    def get_num_skipped_tokens(self, num_computed_tokens: int) -> int:
        """
        Get the number of tokens whose mamba state are not needed anymore. Mamba only
        need to keep the state of the last computed token, so we return
        num_computed_tokens - 1.
        """
        return num_computed_tokens - 1

    def cache_blocks(
        self,
        request: Request,
        num_tokens: int,
        retention_interval: int | None = None,
    ) -> None:
        num_cached_blocks_before = self.num_cached_block.get(request.request_id, 0)
        super().cache_blocks(request, num_tokens, retention_interval=retention_interval)
        num_cached_blocks_after = self.num_cached_block.get(request.request_id, 0)
        if self.mamba_cache_mode == "align":
            partial_hash = self._cache_partial_tail_block(request, num_tokens)
            if partial_hash is not None:
                self.cached_blocks_this_step.add(partial_hash)
        if num_cached_blocks_after > num_cached_blocks_before:
            for block in self.req_to_blocks[request.request_id][
                num_cached_blocks_before:num_cached_blocks_after
            ]:
                # Skip null blocks (align-mode skipped states) and blocks that
                # were not cached this step — with sparse retention
                # (reachable_block_mask) the intermediate state snapshots carry
                # no hash and must not be recorded as cached-this-step.
                if block.is_null or block.block_hash is None:
                    continue
                self.cached_blocks_this_step.add(block.block_hash)

    def new_step_starts(self) -> None:
        self.cached_blocks_this_step.clear()

    def _cache_partial_tail_block(
        self,
        request: Request,
        num_tokens: int,
    ) -> BlockHashWithGroupId | None:
        hash_block_size = self.block_pool.hash_block_size
        if self.block_size == hash_block_size:
            return None
        if num_tokens % self.block_size == 0:
            return None
        if num_tokens % hash_block_size != 0:
            return None
        latest_prompt_hash_boundary = (
            request.num_prompt_tokens // hash_block_size
        ) * hash_block_size
        if num_tokens != latest_prompt_hash_boundary:
            return None

        block_idx = num_tokens // self.block_size
        blocks = self.req_to_blocks[request.request_id]
        if block_idx >= len(blocks):
            return None
        source_block = blocks[block_idx]
        if source_block.is_null:
            return None

        partial_hash = self.block_pool.cache_partial_block(
            request=request,
            block=source_block,
            num_tokens=num_tokens,
            kv_cache_group_id=self.kv_cache_group_id,
            block_size=self.block_size,
        )
        if partial_hash is not None:
            self._partial_hit_reqs[request.request_id] = (block_idx, source_block)
            self.num_cached_block[request.request_id] = block_idx
            # Producer of this partial tail: the boundary state currently lives
            # in ``source_block`` but the next step's forward overwrites it. The
            # upcoming CoW copies it into a durable cow_block; record the req so
            # allocate_new_blocks hands that block to the connector for offload.
            self._producer_partial_tail_reqs[request.request_id] = num_tokens
        return partial_hash


class CrossAttentionManager(SingleTypeKVCacheManager):
    """Manager for cross-attention KV cache in encoder-decoder models."""

    def add_local_computed_blocks(
        self,
        request_id: str,
        new_computed_blocks: Sequence[KVCacheBlock],
        num_local_computed_tokens: int,
        num_external_computed_tokens: int,
    ) -> None:
        # We do not cache blocks for cross-attention to be shared between
        # requests, so  `new_computed_blocks` should always be empty.
        assert len(new_computed_blocks) == 0

    def allocate_external_computed_blocks(
        self,
        request_id: str,
        num_local_computed_tokens: int,
        num_external_computed_tokens: int,
    ) -> None:
        # Cross-attention does not use prefix caching / external KV loads.
        return

    def cache_blocks(
        self,
        request: Request,
        num_tokens: int,
        retention_interval: int | None = None,
    ) -> None:
        # We do not cache blocks for cross-attention to be shared between
        # requests, so this method is not relevant.
        raise ValueError("Should not be called as prefix caching is disabled.")

    def get_num_common_prefix_blocks(self, running_request_id: str) -> int:
        # Cross-attention blocks contain request-specific encoder states
        # and are not shared between different requests
        return 0

    @classmethod
    def find_longest_cache_hit(
        cls,
        block_hashes: BlockHashList,
        max_length: int,
        kv_cache_group_ids: list[int],
        block_pool: BlockPool,
        kv_cache_spec: KVCacheSpec,
        drop_eagle_block: bool,
        alignment_tokens: int,
        dcp_world_size: int = 1,
        pcp_world_size: int = 1,
    ) -> tuple[tuple[list[KVCacheBlock], ...], int]:
        assert isinstance(kv_cache_spec, CrossAttentionSpec), (
            "CrossAttentionManager can only be used for cross-attention groups"
        )
        # Cross-attention does not benefit from prefix caching since:
        # 1. Encoder states are unique per request (different audio/image
        #    inputs)
        # 2. Encoder states are computed once per request, not incrementally
        # 3. No reusable prefix exists between different multimodal inputs
        # Return empty blocks to indicate no cache hits
        raise NotImplementedError("CrossAttentionManager does not support caching")


class SinkFullAttentionManager(FullAttentionManager):
    def __init__(
        self,
        kv_cache_spec: SinkFullAttentionSpec,
        block_pool: BlockPool,
        enable_caching: bool,
        kv_cache_group_id: int,
        scheduler_block_size: int,
        dcp_world_size: int = 1,
        pcp_world_size: int = 1,
    ):
        super().__init__(
            kv_cache_spec=kv_cache_spec,
            block_pool=block_pool,
            enable_caching=enable_caching,
            kv_cache_group_id=kv_cache_group_id,
            scheduler_block_size=scheduler_block_size,
            dcp_world_size=dcp_world_size,
            pcp_world_size=pcp_world_size,
        )
        sink_len = kv_cache_spec.sink_len
        assert sink_len is not None and sink_len > 0 and sink_len % self.block_size == 0
        num_sink_block = sink_len // self.block_size
        self.sink_blocks = self.block_pool.free_block_queue.popleft_n(num_sink_block)


def get_manager_for_kv_cache_spec(
    kv_cache_spec: KVCacheSpec,
    max_in_flight_tokens: int,
    max_model_len: int,
    **kwargs,
) -> SingleTypeKVCacheManager:
    """
    Get the appropriate manager for a given KVCacheSpec.

    Uses the KVCacheSpecRegistry to look up the manager class, supporting
    both built-in and custom specs registered via @register_kv_cache_spec
    and KVCacheSpecRegistry.register.

    Args:
        kv_cache_spec: The KVCacheSpec instance
        max_in_flight_tokens: The max tokens scheduled but not yet settled
            (one batch per concurrent step); see `VllmConfig.max_in_flight_tokens`
        max_model_len: The maximum context length the model could serve
    Returns:
        An instance of the appropriate SingleTypeKVCacheManager subclass
    """
    manager_class = KVCacheSpecRegistry.get_manager_class(kv_cache_spec)
    assert manager_class is not None, (
        f"No manager registered for KVCacheSpec {type(kv_cache_spec)}"
    )
    # SlidingWindow / ChunkedLocalAttention managers recycle blocks;
    # the runtime admission cap must match the recycling-aware bound the
    # startup pool sizer uses (single source of truth: the spec method).
    # R-SWA also recycles gap blocks but peak physical KV still fits the
    # full-attention bound (prefix + window <= max_model_len), so it inherits
    # FullAttentionSpec sizing without a separate admission cap.
    if isinstance(
        kv_cache_spec,
        (SlidingWindowSpec, ChunkedLocalAttentionSpec),
    ):
        kwargs["max_admission_blocks_per_request"] = (
            kv_cache_spec.max_admission_blocks_per_request(
                max_in_flight_tokens=max_in_flight_tokens,
                max_model_len=max_model_len,
            )
        )
    manager = manager_class(kv_cache_spec, **kwargs)
    return manager


def register_all_kvcache_specs(vllm_config):
    """Built-in spec registration"""
    KVCacheSpecRegistry.register(
        FullAttentionSpec,
        FullAttentionManager,
        uniform_type_base_spec=FullAttentionSpec,
    )

    KVCacheSpecRegistry.register(
        SlidingWindowSpec,
        SlidingWindowManager,
        uniform_type_base_spec=SlidingWindowSpec,
    )
    KVCacheSpecRegistry.register(
        SlidingWindowMLASpec,
        SlidingWindowManager,
        uniform_type_base_spec=SlidingWindowMLASpec,
    )

    KVCacheSpecRegistry.register(
        MambaSpec, MambaManager, uniform_type_base_spec=MambaSpec
    )
    KVCacheSpecRegistry.register(
        ChunkedLocalAttentionSpec,
        ChunkedLocalAttentionManager,
        uniform_type_base_spec=ChunkedLocalAttentionSpec,
    )
    KVCacheSpecRegistry.register(
        CrossAttentionSpec,
        CrossAttentionManager,
        uniform_type_base_spec=CrossAttentionSpec,
    )

    # FullAttentionSpec subclasses — grouped with FullAttentionSpec
    KVCacheSpecRegistry.register(
        MLAAttentionSpec, FullAttentionManager, uniform_type_base_spec=FullAttentionSpec
    )
    KVCacheSpecRegistry.register(
        RSWASpec, RSWAManager, uniform_type_base_spec=FullAttentionSpec
    )
    # NOTE(Mengqing): HiddenStateCacheSpec won't take part in
    # grouping, thus the uniform_type_base_spec is just a
    # placeholder.
    KVCacheSpecRegistry.register(
        HiddenStateCacheSpec,
        FullAttentionManager,
        uniform_type_base_spec=FullAttentionSpec,
    )
    KVCacheSpecRegistry.register(
        SinkFullAttentionSpec,
        SinkFullAttentionManager,
        uniform_type_base_spec=FullAttentionSpec,
    )

    from vllm.platforms import current_platform

    current_platform.register_custom_kv_cache_specs(vllm_config)

--- FILE: tests/test_case.py ---
"""Bounded correctness and reachability test for vllm-040."""
from driver import run

TARGET = "vllm-040"
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
# FullAttentionManager.get_num_common_prefix_blocks

Inspect the marked function in `vllm/v1/core/single_type_kv_cache_manager.py` at the pinned revision.
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
  "id": "vllm-040",
  "title": "FullAttentionManager.get_num_common_prefix_blocks body",
  "language": "python",
  "region": {
    "symbol": "FullAttentionManager.get_num_common_prefix_blocks",
    "start_line": 824,
    "end_line": 831,
    "kind": "function"
  },
  "marker": {
    "kind": "python-context",
    "name": "vllm-040",
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
    "path": "vllm/v1/core/single_type_kv_cache_manager.py",
    "sha256": "dc6d2e64cc4cd8cbb3f4bd77d2d035038658d75b6e52f9ace0cf637a4897f71f"
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
    "coverage_note": "Runs explicitly enabled prefix caching with three prompts sharing a prefix longer than a cache block, then a second shared-prefix batch. Cache state and scheduling still determine the marked-path choice; Probe.finish requires observed entry."
  }
}
