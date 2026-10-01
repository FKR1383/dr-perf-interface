# vllm-067 full-feedback result

Status: `success`; iterations: 1; fixed workload: `e938614cecf09efbdebea5ef22a219406334dabb7c3f77bb9231b724dec6438a`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `scheduled_tokens = scheduler_output.total_num_scheduled_tokens`; `scheduled_requests = len(scheduler_output.num_scheduled_tokens)`; `attention_pairs = sum((scheduler_output.num_scheduled_tokens[r.req_id] * (2 * r.num_computed_tokens + scheduler_output.num_scheduled_tokens[r.req_id] + 1) // 2 for r in scheduler_output.scheduled_new_reqs)) + sum((scheduler_output.num_scheduled_tokens[r] * (2 * self.requests[r].num_computed_tokens + scheduler_output.num_scheduled_tokens[r] + 1) // 2 for r in scheduler_output.scheduled_cached_reqs.req_ids))`; `new_requests = len(scheduler_output.scheduled_new_reqs)` | 5.48765% | success |
