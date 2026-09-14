# Collection provenance

Source: [get_request_block_hasher.request_block_hasher](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/core/kv_cache_utils.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-kv/vllm/v1/core/kv_cache_utils.py`: `perfmark.region('kv_block_hasher', num_hashes=len(request.block_hashes), num_tokens=request.num_tokens)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
