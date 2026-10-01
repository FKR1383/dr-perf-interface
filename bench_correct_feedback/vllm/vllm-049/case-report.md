# vllm-049 full-feedback result

Status: `success`; iterations: 2; fixed workload: `77909abfee49a2c509c2a876ef1995b97c58d79af5ee9c2aa6047d68a89ac552`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `prompt_length = len(prompt_token_ids) if prompt_token_ids is not None else int(prompt_embeds.shape[0]) if prompt_embeds is not None else 0` | 57.6292% | retry |
| 2 | `prompt_length = len(prompt_token_ids) if prompt_token_ids is not None else 0`; `single_token_prompt = int(prompt_token_ids is not None and len(prompt_token_ids) == 1)`; `two_token_prompt = int(prompt_token_ids is not None and len(prompt_token_ids) == 2)`; `periodic_elevated_state = int(prompt_token_ids is not None and len(prompt_token_ids) % 7 == 5)` | 0% | success |
