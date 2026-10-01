# vllm-026 full-feedback result

Status: `success`; iterations: 2; fixed workload: `cd14cde9a4fb665a3297d2413cc1cc278413b8235b22a4ef5475a538327f4185`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `allocated_blocks = sum((len(manager.req_to_blocks.get(request.request_id, ())) for manager in self.kv_cache_manager.coordinator.single_type_managers)) if not delay_free_blocks else 0`; `last_reference_blocks = sum((block.ref_cnt == 1 for manager in self.kv_cache_manager.coordinator.single_type_managers for block in manager.req_to_blocks.get(request.request_id, ()))) if not delay_free_blocks else 0` | - | invalid |
| 2 | `active_requests = len(self.requests)`; `finished_requests = len(self.finished_req_ids)`; `allocated_blocks = sum((len(manager.req_to_blocks.get(request.request_id, ())) for manager in self.kv_cache_manager.coordinator.single_type_managers)) if not delay_free_blocks else 0` | 6.61014% | success |
