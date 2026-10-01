# vllm-050 full-feedback result

Status: `success`; iterations: 2; fixed workload: `23126f93fb758a60ed74e567656725c800a637463bfe11482575f0418b628cc4`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `row_count = len(output_token_ids)`; `token_count = sum((len(row) for row in output_token_ids))`; `padded_elements = len(output_token_ids) * max((len(row) for row in output_token_ids), default=0)` | 24.2466% | retry |
| 2 | `row_count = len(output_token_ids)`; `token_count = sum((len(row) for row in output_token_ids))`; `padded_elements = len(output_token_ids) * max((len(row) for row in output_token_ids), default=0)`; `single_element_tensor = int(len(output_token_ids) * max((len(row) for row in output_token_ids), default=0) == 1)` | 1.7795% | success |
