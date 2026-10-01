# vllm-010 full-feedback result

Status: `success`; iterations: 3; fixed workload: `ecacc321a55fa07cb7cc03fd3e337574e0d78d7642b22a2040e5d86833c586a4`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `new_full_blocks = max(0, num_tokens_to_cache // self.coordinator.single_type_managers[0].block_size - self.coordinator.single_type_managers[0].num_cached_block.get(request.request_id, 0))`; `has_new_full_blocks = int(num_tokens_to_cache // self.coordinator.single_type_managers[0].block_size > self.coordinator.single_type_managers[0].num_cached_block.get(request.request_id, 0))` | - | invalid |
| 2 | `tokens_to_cache = num_tokens_to_cache` | 18.7295% | retry |
| 3 | `output_tokens = request.num_output_tokens` | 0% | success |
