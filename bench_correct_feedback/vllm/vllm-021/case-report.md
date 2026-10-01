# vllm-021 full-feedback result

Status: `success`; iterations: 2; fixed workload: `7502f6d7b3f9c490cd1b18f07b5a241d1a496ac1b454d342aeaec03e52ed5c3d`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `heap_nonempty = int(bool(self._heap))` | - | invalid |
| 2 | `heap_size = len(self._heap)` | 0% | success |
