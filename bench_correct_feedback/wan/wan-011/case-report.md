# wan-011 full-feedback result

Status: `success`; iterations: 1; fixed workload: `e2d3b2126dab5e3a24c11b5b07727722b396754bb02f43e9191e09087b436fe9`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `temporal_chunks = 1 + (x.shape[2] - 1) // 4`; `spatial_area = x.shape[0] * x.shape[3] * x.shape[4]`; `subsequent_chunk_area = x.shape[0] * ((x.shape[2] - 1) // 4) * x.shape[3] * x.shape[4]`; `attention_pairs = x.shape[0] * (1 + (x.shape[2] - 1) // 4) * (x.shape[3] // 8 * (x.shape[4] // 8)) ** 2` | 4.24678% | success |
