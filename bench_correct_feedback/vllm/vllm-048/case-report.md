# vllm-048 full-feedback result

Status: `success`; iterations: 2; fixed workload: `cff3752569fb39da444bb467c2380e3851568bb416cc484d87e822a4d091ba01`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `finished = int(finish_reason is not None)`; `new_token_count = len(new_token_ids)` | 34.4667% | retry |
| 2 | `finished = int(finish_reason is not None)`; `new_token_count = len(new_token_ids)`; `single_token_output = int(len(new_token_ids) == 1)`; `two_token_output = int(len(new_token_ids) == 2)` | 9.51271% | success |
