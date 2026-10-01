# vllm-014 full-feedback result

Status: `success`; iterations: 2; fixed workload: `bbe309dc89d07c87a1834077955b5d2470ea1ca1891befcbb99cac93fc3c561f`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `append_operation = 1`; `empty_queue = int(len(self) == 0)` | - | invalid |
| 2 | `queue_depth = len(self)`; `empty_queue = int(len(self) == 0)` | 0% | success |
