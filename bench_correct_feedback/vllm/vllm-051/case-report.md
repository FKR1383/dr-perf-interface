# vllm-051 full-feedback result

Status: `success`; iterations: 2; fixed workload: `898bc885f8f6d43363d31072795bcb148c6df7406bcd4d64a115da0b3e9bae5f`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `batch_size = len(output_token_ids)`; `logit_elements = logits.numel()`; `prompt_elements = prompt_token_ids.numel()`; `padded_output_elements = len(output_token_ids) * max((len(row) for row in output_token_ids), default=0)` | 34.1819% | retry |
| 2 | `batch_size = len(output_token_ids)`; `logit_elements = logits.numel()`; `prompt_elements = prompt_token_ids.numel()`; `singleton_batch = int(len(output_token_ids) == 1)` | 3.94546% | success |
