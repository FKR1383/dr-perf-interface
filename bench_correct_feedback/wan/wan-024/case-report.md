# wan-024 full-feedback result

Status: `success`; iterations: 3; fixed workload: `9e9db6b65c85c9f5e43f7675aa549ef9f2429cf8375c73fd3ac84f6265d51ffe`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `hidden_elements = hidden_states.numel()`; `encoder_elements = encoder_hidden_states.numel()`; `self_attention_work = hidden_states.shape[0] * hidden_states.shape[1] ** 2 * hidden_states.shape[2]`; `cross_attention_work = hidden_states.shape[0] * hidden_states.shape[1] * encoder_hidden_states.shape[1] * hidden_states.shape[2]` | 10.6143% | retry |
| 2 | `hidden_elements = hidden_states.numel()`; `encoder_elements = encoder_hidden_states.numel()`; `attention_work = hidden_states.shape[0] * hidden_states.shape[1] * (hidden_states.shape[1] + encoder_hidden_states.shape[1]) * hidden_states.shape[2]`; `token_tile_remainder = hidden_states.shape[0] * (hidden_states.shape[1] % 16)` | 10.0904% | retry |
| 3 | `hidden_elements = hidden_states.numel()`; `encoder_elements = encoder_hidden_states.numel()`; `attention_work = hidden_states.shape[0] * hidden_states.shape[1] * (hidden_states.shape[1] + encoder_hidden_states.shape[1]) * hidden_states.shape[2]`; `token_tile_remainder = hidden_states.shape[0] * (hidden_states.shape[1] % 8)` | 9.1626% | success |
