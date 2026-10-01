# wan-029 full-feedback result

Status: `success`; iterations: 2; fixed workload: `9d32790b8cd59b63dd4bc6c3ba0f173e4fe2ad571dae306802a33f55ffaf1ab9`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `timestep_elements = latents.shape[0] * (latents.shape[2] * ((latents.shape[3] + 1) // 2) * ((latents.shape[4] + 1) // 2) if self.config.expand_timesteps else 1)` | - | invalid |
| 2 | `prompt_sequence_length = prompt_embeds.shape[1]` | 0% | success |
