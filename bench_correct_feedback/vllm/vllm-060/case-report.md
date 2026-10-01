# vllm-060 full-feedback result

Status: `success`; iterations: 2; fixed workload: `2df2d18b6ac71d6f2ee680067f6e7b6f5a7b3f697e7551ca5a1a9c067886b8ff`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `sampling_copy_count = int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + 3 * int(not self.no_penalties)`; `penalties_enabled = int(not self.no_penalties)`; `prompt_rows = self.num_reqs if not self.no_penalties else 0`; `prompt_elements = self.num_reqs * int(max(self.num_prompt_tokens[:self.num_reqs])) if self.num_reqs and (not self.no_penalties) else 0` | 13.8905% | retry |
| 2 | `sampling_copy_count = int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + 3 * int(not self.no_penalties)`; `penalties_enabled = int(not self.no_penalties)`; `prompt_rows = self.num_reqs if not self.no_penalties else 0`; `empty_batch = int(self.num_reqs == 0)` | 6.477% | success |
