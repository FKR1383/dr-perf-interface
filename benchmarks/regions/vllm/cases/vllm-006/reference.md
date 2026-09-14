# Collection provenance

Source: [KVCacheManager.allocate_slots](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/core/kv_cache_manager.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-kv/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('kv_allocate_slots', num_new_tokens=num_new_tokens, num_computed=request.num_computed_tokens)`
- `vllm-cpu-sched/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('alloc_cache', num_cache=num_tokens_to_cache)`
- `vllm-cpu-sched/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('alloc_count', num_slot=num_tokens_need_slot)`
- `vllm-cpu-sched/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('alloc_new', num_slot=num_tokens_need_slot)`
- `vllm-cpu-sched/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('alloc_skipped', num_computed=total_computed_tokens)`
- `vllm-cpu-sched/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('alloc_wrap', n=0)`
- `vllm-cpu-sched/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('kv_allocate_slots', num_new_tokens=num_new_tokens, num_computed=request.num_computed_tokens, num_new_computed=num_new_computed_tokens, num_tokens=request.num_tokens)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
