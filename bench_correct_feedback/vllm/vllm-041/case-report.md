# vllm-041 full-feedback result

Status: `success`; iterations: 1; fixed workload: `1c8bf8261f2c1c91f331b21bd6e756823d67cfb06533bfef639e58e66a4533f9`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `waiting_depth = len(self.scheduler.waiting)`; `heap_height = int(len(self.scheduler.waiting) > 0) + int(len(self.scheduler.waiting) > 1) + int(len(self.scheduler.waiting) > 3) + int(len(self.scheduler.waiting) > 7)`; `highest_priority = int(request.priority == 0)`; `empty_waiting_queue = int(len(self.scheduler.waiting) == 0)` | 5.44649% | success |
