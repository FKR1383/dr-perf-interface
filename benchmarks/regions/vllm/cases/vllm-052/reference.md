# Collection provenance

Source: [TopKTopPSampler.forward_cpu](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/sample/ops/topk_topp_sampler.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-samp/vllm/v1/sample/ops/topk_topp_sampler.py`: `perfmark.region('topk_topp', num_reqs=logits.shape[0], k=int(k.max()) if k is not None else 0, p_flag=1 if p is not None else 0)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
