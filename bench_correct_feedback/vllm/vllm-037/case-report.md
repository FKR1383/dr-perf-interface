# vllm-037 full-feedback result

Status: `success`; iterations: 2; fixed workload: `d94390f3ac71ba1fda999b150849f9254d123a20ec8c72540ee8ec7215351563`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `skipped_count = len(step_skipped_waiting)`; `has_skipped = int(bool(step_skipped_waiting))`; `update_capacity_bound = int(not defer_prefills)` | - | invalid |
| 2 | `running_count = len(self.running)`; `skipped_count = len(step_skipped_waiting)`; `update_capacity_bound = int(not defer_prefills)` | 0% | success |
