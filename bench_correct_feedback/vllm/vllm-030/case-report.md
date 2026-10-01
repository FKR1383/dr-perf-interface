# vllm-030 full-feedback result

Status: `success`; iterations: 3; fixed workload: `8eb6d70fe60623b2729daa842cd8e42e6a6b7fe234f8ebf98236010cbf25c786`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `waiting_depth = len(self.waiting)`; `heap_height = 0 if len(self.waiting) == 0 else 1 if len(self.waiting) < 3 else 2 if len(self.waiting) < 7 else 3`; `incoming_priority = request.priority` | 17.0864% | retry |
| 2 | `waiting_depth = len(self.waiting)`; `heap_height = 0 if len(self.waiting) == 0 else 1 if len(self.waiting) < 3 else 2 if len(self.waiting) < 7 else 3`; `incoming_priority = request.priority`; `prompt_tokens = request.num_prompt_tokens` | 35.5365% | retry |
| 3 | `waiting_depth = len(self.waiting)`; `sift_levels = (1 if len(self.waiting) >= 1 and request < self.waiting._heap[(len(self.waiting) - 1) // 2] else 0) + (1 if len(self.waiting) >= 3 and request < self.waiting._heap[(len(self.waiting) - 3) // 4] else 0) + (1 if len(self.waiting) >= 7 and request < self.waiting._heap[(len(self.waiting) - 7) // 8] else 0)` | 6.59503% | success |
