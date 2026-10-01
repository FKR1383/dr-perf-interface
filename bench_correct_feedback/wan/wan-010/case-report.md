# wan-010 full-feedback result

Status: `success`; iterations: 1; fixed workload: `78fe9fcc2e058c657f2e36b91775719579cfe7a0921829839ff4ba253ff743e2`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `latent_frames = z.shape[2]`; `first_frame_area = z.shape[0] * z.shape[3] * z.shape[4]`; `subsequent_frame_area = z.shape[0] * (z.shape[2] - 1) * z.shape[3] * z.shape[4]`; `attention_pairs = z.shape[0] * z.shape[2] * (z.shape[3] * z.shape[4]) ** 2` | 3.61893% | success |
