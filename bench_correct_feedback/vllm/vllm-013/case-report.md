# vllm-013 full-feedback result

Status: `success`; iterations: 2; fixed workload: `5f00eac657525e2c6fff57ddd974b54402cd14e9e3895ee1e5ee46511f913e3b`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `new_full_blocks = max(0, request.num_tokens // hash_block_size - len(request.block_hashes))`; `hashing_active = int(request.num_tokens // hash_block_size > len(request.block_hashes))`; `new_full_block_tokens = max(0, request.num_tokens // hash_block_size - len(request.block_hashes)) * hash_block_size` | - | invalid |
| 2 | `num_tokens = request.num_tokens`; `new_full_blocks = max(0, request.num_tokens // hash_block_size - len(request.block_hashes))` | 0% | success |
