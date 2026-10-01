# wan-025 full-feedback result

Status: `success`; iterations: 2; fixed workload: `27359e61ef134af714c23c0befcb1d3a221123d691a7f2d9347de7190de65960`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `denoising_steps = num_inference_steps`; `step_text_tokens = num_inference_steps * prompt_embeds.shape[1]` | 17.0409% | retry |
| 2 | `denoising_steps = num_inference_steps`; `step_text_tokens = num_inference_steps * prompt_embeds.shape[1]`; `loaded_modules = len(__import__('sys').modules)`; `steps_loaded_modules = num_inference_steps * len(__import__('sys').modules)` | 8.96086% | success |
