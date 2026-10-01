# vllm-033 full-feedback result

Status: `success`; iterations: 3; fixed workload: `30f279e661826197509547e6b241d571ed7d0d8eafddb4538fa819f91749ecfe`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `existing_full_blocks = request.num_computed_tokens // self.block_size`; `needs_new_block = int(request.num_computed_tokens % self.block_size == 0)`; `completes_full_block = int((request.num_computed_tokens + 1) % self.block_size == 0)` | - | invalid |
| 2 | `sequence_tokens = request.num_computed_tokens`; `running_requests = len(self.running)` | 20.5332% | retry |
| 3 | `sequence_tokens = request.num_computed_tokens`; `running_requests = len(self.running)`; `short_prompt_first_decode = int(request.num_prompt_tokens < 16 and request.num_output_tokens == 1)`; `short_prompt_first_decode_length = request.num_prompt_tokens if request.num_prompt_tokens < 16 and request.num_output_tokens == 1 else 0` | 2.25123% | success |
