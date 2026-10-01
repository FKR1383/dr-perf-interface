# vllm-023 full-feedback result

Status: `success`; iterations: 2; fixed workload: `5f095c2e923b6f64b2bf1d04db8322bc54c16096a04196d08becf4f3503b7b54`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `first_sift_swap = int(bool(self._heap) and (request.priority, request.arrival_time) < (self._heap[(len(self._heap) - 1) // 2].priority, self._heap[(len(self._heap) - 1) // 2].arrival_time))`; `second_comparison = int(len(self._heap) >= 3 and (request.priority, request.arrival_time) < (self._heap[(len(self._heap) - 1) // 2].priority, self._heap[(len(self._heap) - 1) // 2].arrival_time))`; `parent_priority_tie = int(bool(self._heap) and request.priority == self._heap[(len(self._heap) - 1) // 2].priority)`; `list_capacity_exhausted = int(self._heap.__sizeof__() == [].__sizeof__() + 8 * len(self._heap))` | - | invalid |
| 2 | `first_sift_swap = int(bool(self._heap) and (request.priority, request.arrival_time) < (self._heap[(len(self._heap) - 1) // 2].priority, self._heap[(len(self._heap) - 1) // 2].arrival_time))`; `shallow_root_insertion = int(0 < len(self._heap) < 3 and (request.priority, request.arrival_time) < (self._heap[0].priority, self._heap[0].arrival_time))`; `list_capacity_exhausted = int(self._heap.__sizeof__() == [].__sizeof__() + 8 * len(self._heap))`; `incoming_priority = request.priority` | 0% | success |
