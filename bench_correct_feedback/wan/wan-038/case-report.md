# wan-038 full-feedback result

Status: `success`; iterations: 1; fixed workload: `f506703147a9440cb8e2de6b94b8f61b0f6308777744c8461fac9328dde3ca4a`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `schedule_length = num_inference_steps if num_inference_steps is not None else len(sigmas) if sigmas is not None else len(timesteps)`; `singleton_schedule = int((num_inference_steps if num_inference_steps is not None else len(sigmas) if sigmas is not None else len(timesteps)) == 1)` | 0% | success |
