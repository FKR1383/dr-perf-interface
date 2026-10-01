# wan-026 full-feedback result

Status: `success`; iterations: 3; fixed workload: `39be52c5c8b8b33c748dd1ce77571405e796a315d8b13bdd0fa573c1ad6905ca`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `text_length = prompt_embeds.shape[1]`; `scheduler_initialization = int(self.scheduler.step_index is None)` | 15.816% | retry |
| 2 | `text_length = prompt_embeds.shape[1]`; `scheduler_initialization = int(self.scheduler.step_index is None)`; `gc_allocation_pressure = __import__('gc').get_count()[0]`; `gc_older_generation_pressure = __import__('gc').get_count()[1]` | 39.3377% | retry |
| 3 | `text_length = prompt_embeds.shape[1]` | 5.53132% | success |
