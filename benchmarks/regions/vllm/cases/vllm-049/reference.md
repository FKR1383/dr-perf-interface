# Collection provenance

Source: [Request.__init__](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/request.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-req/vllm/v1/request.py`: `perfmark.region('request_init', num_prompt=len(prompt_token_ids) if prompt_token_ids is not None else 0, num_blocks=len(prompt_token_ids) // getattr(block_hasher, 'hash_block_size', 0) if prompt_token_ids and getattr(block_hasher, 'hash_block_size', 0) else 0)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
