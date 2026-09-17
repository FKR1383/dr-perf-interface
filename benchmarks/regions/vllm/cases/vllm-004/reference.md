# Collection provenance

Source: [CPUAttentionBackendImpl.forward](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/attention/backends/cpu_attn.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-batch/vllm/v1/attention/backends/cpu_attn.py`: `perfmark.region('attention', num_tokens=query.shape[0], kv_tokens=int(attn_metadata.seq_lens.sum()) if attn_metadata is not None else 0)`
- `vllm-cpu-kv/vllm/v1/attention/backends/cpu_attn.py`: `perfmark.region('attention', num_tokens=query.shape[0], kv_tokens=int(attn_metadata.seq_lens.sum()) if attn_metadata is not None else 0)`
- `vllm-cpu-out/vllm/v1/attention/backends/cpu_attn.py`: `perfmark.region('attention', num_tokens=query.shape[0], kv_tokens=int(attn_metadata.seq_lens.sum()) if attn_metadata is not None else 0)`
- `vllm-cpu-req/vllm/v1/attention/backends/cpu_attn.py`: `perfmark.region('attention', num_tokens=query.shape[0], kv_tokens=int(attn_metadata.seq_lens.sum()) if attn_metadata is not None else 0)`
- `vllm-cpu-samp/vllm/v1/attention/backends/cpu_attn.py`: `perfmark.region('attention', num_tokens=query.shape[0], kv_tokens=int(attn_metadata.seq_lens.sum()) if attn_metadata is not None else 0)`
- `vllm-cpu-sched/vllm/v1/attention/backends/cpu_attn.py`: `perfmark.region('attention', num_tokens=query.shape[0], kv_tokens=int(attn_metadata.seq_lens.sum()) if attn_metadata is not None else 0)`
- `vllm-cpu-spec/vllm/v1/attention/backends/cpu_attn.py`: `perfmark.region('attention', num_tokens=query.shape[0], kv_tokens=int(attn_metadata.seq_lens.sum()) if attn_metadata is not None else 0)`
- `vllm-cpu-src/vllm/v1/attention/backends/cpu_attn.py`: `perfmark.region('attention', num_tokens=query.shape[0], kv_tokens=int(attn_metadata.seq_lens.sum()) if attn_metadata is not None else 0)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
