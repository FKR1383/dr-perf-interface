# Collection provenance

Source: [KVCacheManager.free](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/core/kv_cache_manager.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-kv/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('kv_free', num_blocks=len(self.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())), num_tokens=request.num_tokens)`
- `vllm-cpu-req/vllm/v1/core/kv_cache_manager.py`: `perfmark.region('kv_free', num_blocks=len(self.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())), num_tokens=request.num_tokens)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
