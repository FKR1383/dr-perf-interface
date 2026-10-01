# vllm-011 full-feedback result

Status: `success`; iterations: 2; fixed workload: `97a92bd41431eaa53105d4c3c38f28bd2153fc9cd346abfc48ec51a1edf315b3`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `blocks_released = sum((len(mgr.req_to_blocks.get(request.request_id, ())) for mgr in self.coordinator.single_type_managers)) + len(self._partial_tail_pins.get(request.request_id, ()))`; `blocks_becoming_free = sum((block.ref_cnt == 1 and (not block.is_null) for mgr in self.coordinator.single_type_managers for block in mgr.req_to_blocks.get(request.request_id, ()))) + sum((block.ref_cnt == 1 and (not block.is_null) for block in self._partial_tail_pins.get(request.request_id, ())))` | - | invalid |
| 2 | `blocks_released = sum((len(mgr.req_to_blocks.get(request.request_id, ())) for mgr in self.coordinator.single_type_managers)) + len(self._partial_tail_pins.get(request.request_id, ()))`; `tracked_requests = sum((len(mgr.req_to_blocks) for mgr in self.coordinator.single_type_managers))` | 1.3314% | success |
