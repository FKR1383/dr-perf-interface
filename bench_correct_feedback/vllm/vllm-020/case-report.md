# vllm-020 full-feedback result

Status: `success`; iterations: 1; fixed workload: `d0e8d80425e60d167459bf6399d4f1c1afc3dff12180e66e725f453cbd86d7df`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `sift_depth = int(len(self._heap) >= 1) + int(len(self._heap) >= 3) + int(len(self._heap) >= 7)`; `list_growth = int(len(self._heap) == 4 or len(self._heap) == 8)`; `empty_heap = int(len(self._heap) == 0)` | 4.16048% | success |
