# wan-013 full-feedback result

Status: `success`; iterations: 1; fixed workload: `2246d4fca046378abefd84441e43598ff5e152734d856f6c3f4008ba51fd0244`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `spatial_tiles = (x.shape[3] + self.tile_sample_stride_height - 1) // self.tile_sample_stride_height * ((x.shape[4] + self.tile_sample_stride_width - 1) // self.tile_sample_stride_width)`; `cached_tile_chunks = (x.shape[3] + self.tile_sample_stride_height - 1) // self.tile_sample_stride_height * ((x.shape[4] + self.tile_sample_stride_width - 1) // self.tile_sample_stride_width) * ((x.shape[2] - 1) // 4)`; `first_chunk_tile_area = x.shape[0] * ((x.shape[3] - 1) // self.tile_sample_stride_height * self.tile_sample_min_height + (x.shape[3] - 1) % self.tile_sample_stride_height + 1) * ((x.shape[4] - 1) // self.tile_sample_stride_width * self.tile_sample_min_width + (x.shape[4] - 1) % self.tile_sample_stride_width + 1)`; `cached_chunk_tile_area = x.shape[0] * ((x.shape[3] - 1) // self.tile_sample_stride_height * self.tile_sample_min_height + (x.shape[3] - 1) % self.tile_sample_stride_height + 1) * ((x.shape[4] - 1) // self.tile_sample_stride_width * self.tile_sample_min_width + (x.shape[4] - 1) % self.tile_sample_stride_width + 1) * ((x.shape[2] - 1) // 4)` | 5.09705% | success |
