# vllm-005 full-feedback result

Status: `success`; iterations: 2; fixed workload: `638f94e41943f192895fbd17e68d72344bfefef27c9fd71609f26fbba5d7b04a`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `new_block_count = max(0, num_full_blocks - num_cached_blocks)` | 19.5693% | retry |
| 2 | `new_block_count = max(0, num_full_blocks - num_cached_blocks)`; `single_block_batch = int(num_full_blocks - num_cached_blocks == 1)`; `two_block_batch = int(num_full_blocks - num_cached_blocks == 2)` | 1.89619% | success |
