# vllm-008 full-feedback result

Status: `success`; iterations: 3; fixed workload: `9f0e8a724f225ddc4534162ff5c6c3a385ac129c9e7406d944948753ea0627c2`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `prefix_blocks = len(new_computed_block_list[0])`; `has_prefix_blocks = int(bool(new_computed_block_list[0]))`; `has_existing_blocks = int(bool(self.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())))`; `needs_additional_blocks = int((num_tokens_need_slot + self.coordinator.single_type_managers[0].block_size - 1) // self.coordinator.single_type_managers[0].block_size > len(self.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())) + len(new_computed_block_list[0]))` | - | invalid |
| 2 | `tokens_needing_slots = num_tokens_need_slot`; `has_existing_blocks = int(bool(self.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())))` | 19.9741% | retry |
| 3 | `tracked_requests = len(self.coordinator.single_type_managers[0].req_to_blocks)`; `has_existing_blocks = int(bool(self.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())))` | 0% | success |
