# vllm-003 full-feedback result

Status: `success`; iterations: 1; fixed workload: `132be157203be0098466d2c7df6f65989232b57cef3f9847f17714366eafd1fb`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `request_count_proxy = int(use_tqdm) + 1`; `decode_rounds_proxy = 2 * int(use_tqdm) + 1 if use_tqdm < 2 else 4`; `long_prompt_requests = int(use_tqdm) + 1 if use_tqdm >= 4 else 0`; `initial_batch = int(use_tqdm == 0)` | 2.52508% | success |
