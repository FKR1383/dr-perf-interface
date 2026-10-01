# vllm-017 full-feedback result

Status: `success`; iterations: 2; fixed workload: `986ecef7ce2fd840b2b171da0ebdc50aa3336d7814547f18dcf160372337dc7f`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `constant_work = 1` | - | invalid |
| 2 | `queue_length = len(self)` | 0% | success |
