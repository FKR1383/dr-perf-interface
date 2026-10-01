# wan-030 full-feedback result

Status: `success`; iterations: 3; fixed workload: `c130dcedd92a3b272e4f896320f2a09cb12ec4516ca9d67ef9acf4383abc38ce`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `noise_elements = noise_pred.numel()` | - | invalid |
| 2 | `noise_elements = noise_pred.numel()`; `conditioning_length = prompt_embeds.shape[1]` | - | invalid |
| 3 | `conditioning_length = prompt_embeds.shape[1]` | 0% | success |
