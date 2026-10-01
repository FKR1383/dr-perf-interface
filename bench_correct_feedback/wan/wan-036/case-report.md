# wan-036 full-feedback result

Status: `success`; iterations: 2; fixed workload: `32dbb465c78f01e116af8d7fca057e59845fce7f90efdd5f069280106b1cf723`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `generated_elements = batch_size * num_channels_latents * ((num_frames - 1) // self.vae_scale_factor_temporal + 1) * (int(height) // self.vae_scale_factor_spatial) * (int(width) // self.vae_scale_factor_spatial) if latents is None else 0` | 14.2687% | retry |
| 2 | `generated_elements = batch_size * num_channels_latents * ((num_frames - 1) // self.vae_scale_factor_temporal + 1) * (int(height) // self.vae_scale_factor_spatial) * (int(width) // self.vae_scale_factor_spatial) if latents is None else 0`; `rng_state_refreshes = (batch_size * num_channels_latents * ((num_frames - 1) // self.vae_scale_factor_temporal + 1) * (int(height) // self.vae_scale_factor_spatial) * (int(width) // self.vae_scale_factor_spatial) + 623) // 624 if latents is None else 0` | 0% | success |
