# vllm-057 full-feedback result

Status: `success`; iterations: 2; fixed workload: `c50352bd875c09b50ae6d3c66bfc9eab31e058039abb8203dc98d6d70dca9f51`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `batch_size = len(sampled_token_ids)`; `sampled_requests = sum((1 for ids in sampled_token_ids if len(ids) > 0))`; `context_tokens = int(sum(num_tokens_no_spec))`; `has_sampled_requests = int(sum((1 for ids in sampled_token_ids if len(ids) > 0)) > 0)` | 99.9751% | retry |
| 2 | `batch_size = len(sampled_token_ids)`; `sampled_requests = sum((1 for ids in sampled_token_ids if len(ids) > 0))`; `has_sampled_requests = int(sum((1 for ids in sampled_token_ids if len(ids) > 0)) > 0)`; `requires_initial_compilation = int(len(batch_propose_numba.signatures) == 0 and sum((1 for ids in sampled_token_ids if len(ids) > 0)) > 0)` | 3.09185% | success |
