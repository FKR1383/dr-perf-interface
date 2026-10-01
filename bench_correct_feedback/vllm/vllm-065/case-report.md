# vllm-065 full-feedback result

Status: `success`; iterations: 2; fixed workload: `0811b4193812c2fecefaf6ed7da5b285d4fa13a8745ffe989379f7b1ba2850d1`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `num_requests = self.input_batch.num_reqs`; `num_scheduled_tokens = scheduler_output.total_num_scheduled_tokens` | 37.8311% | retry |
| 2 | `num_requests = self.input_batch.num_reqs`; `num_scheduled_tokens = scheduler_output.total_num_scheduled_tokens`; `single_request_prefill = int(self.input_batch.num_reqs == 1 and scheduler_output.total_num_scheduled_tokens > self.input_batch.num_reqs)`; `two_request_prefill = int(self.input_batch.num_reqs == 2 and scheduler_output.total_num_scheduled_tokens > self.input_batch.num_reqs)` | 9.79153% | success |
