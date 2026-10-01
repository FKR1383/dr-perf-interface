# wan-037 full-feedback result

Status: `success`; iterations: 1; fixed workload: `5915f48b2d8b350fec3f0ffbf812e7171c7d3872b8934bf9084868b8027e4645`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `schedule_size = (self.timesteps if schedule_timesteps is None else schedule_timesteps).numel()`; `singleton_schedule = int((self.timesteps if schedule_timesteps is None else schedule_timesteps).numel() == 1)` | 0% | success |
