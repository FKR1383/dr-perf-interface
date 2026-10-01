# vllm-007 full-feedback result

Status: `success`; iterations: 2; fixed workload: `5b69afe0adc6e40f0e35d5d2d8d9d3e4c65a9a6ca07d21dfdf7875941148c09a`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `cache_groups = len(self.coordinator.single_type_managers)` | - | invalid |
| 2 | `processed_tokens = max(0, total_computed_tokens - request.num_in_flight_tokens)` | 0% | success |
