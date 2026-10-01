# wan-005 full-feedback result

Status: `success`; iterations: 1; fixed workload: `b34d534f6ef832cbab0df579c271bf69c121f030f01a79e4a5da3954c005a008`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `latent_frames = z.shape[2]`; `first_frame_area = z.shape[0] * z.shape[3] * z.shape[4]`; `subsequent_frame_area = z.shape[0] * (z.shape[2] - 1) * z.shape[3] * z.shape[4]`; `attention_work = z.shape[0] * z.shape[2] * (z.shape[3] * z.shape[4]) ** 2` | 3.83072% | success |
