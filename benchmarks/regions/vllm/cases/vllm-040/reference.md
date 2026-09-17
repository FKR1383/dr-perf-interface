# Collection provenance

Source: [FullAttentionManager.get_num_common_prefix_blocks](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/core/single_type_kv_cache_manager.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-kv/vllm/v1/core/single_type_kv_cache_manager.py`: `perfmark.region('kv_common_prefix_blocks', num_running=len(self.req_to_blocks), num_blocks=len(self.req_to_blocks.get(running_request_id, ())))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
