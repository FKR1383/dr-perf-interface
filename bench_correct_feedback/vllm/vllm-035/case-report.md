# vllm-035 full-feedback result

Status: `success`; iterations: 4; fixed workload: `e0089cc65a4a7aeff1ced94a1a01c7c91a1294c6c5c4a8f7f4abd224aecec46b`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `waiting_requests = len(self.waiting) + len(self.skipped_waiting)`; `waiting_blocks = sum(((r.num_tokens + self.block_size - 1) // self.block_size for r in self.waiting))`; `priority_queue_work = len(self.waiting) * (0 if len(self.waiting) == 0 else 1 if len(self.waiting) < 2 else 2 if len(self.waiting) < 4 else 3 if len(self.waiting) < 8 else 4)` | 58.6501% | retry |
| 2 | `waiting_requests = len(self.waiting) + len(self.skipped_waiting)`; `nonempty_waiting = int(len(self.waiting) + len(self.skipped_waiting) > 0)`; `waiting_requests_squared = (len(self.waiting) + len(self.skipped_waiting)) ** 2` | 43.7965% | retry |
| 3 | `waiting_requests = len(self.waiting) + len(self.skipped_waiting)`; `single_waiting_request = int(len(self.waiting) + len(self.skipped_waiting) == 1)`; `two_waiting_requests = int(len(self.waiting) + len(self.skipped_waiting) == 2)`; `running_with_empty_waiting = len(self.running) if len(self.waiting) + len(self.skipped_waiting) == 0 else 0` | 13.9998% | retry |
| 4 | `waiting_requests = len(self.waiting) + len(self.skipped_waiting)`; `single_waiting_request = int(len(self.waiting) + len(self.skipped_waiting) == 1)`; `two_waiting_requests = int(len(self.waiting) + len(self.skipped_waiting) == 2)`; `nonempty_waiting = int(len(self.waiting) + len(self.skipped_waiting) > 0)` | 6.06685% | success |
