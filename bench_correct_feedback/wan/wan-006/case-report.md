# wan-006 full-feedback result

Status: `success`; iterations: 1; fixed workload: `2a874d13baa67b6709ea37ebd897702edf1138939fc3b12f8bd70c3127b89c16`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `temporal_chunks = 1 + (x.shape[2] - 1) // 4`; `spatial_area = x.shape[0] * x.shape[3] * x.shape[4]`; `chunk_spatial_work = x.shape[0] * (1 + (x.shape[2] - 1) // 4) * x.shape[3] * x.shape[4]`; `attention_pair_work = x.shape[0] * (1 + (x.shape[2] - 1) // 4) * (x.shape[3] // 8 * (x.shape[4] // 8)) ** 2` | 4.86558% | success |
