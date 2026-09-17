# Collection provenance

Source: [apply_all_penalties](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/sample/ops/penalties.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-samp/vllm/v1/sample/ops/penalties.py`: `perfmark.region('apply_penalties', num_reqs=len(output_token_ids), max_len=max((len(o) for o in output_token_ids), default=0), total_tokens=sum((len(o) for o in output_token_ids)))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
