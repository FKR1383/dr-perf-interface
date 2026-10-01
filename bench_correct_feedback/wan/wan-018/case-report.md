# wan-018 full-feedback result

Status: `success`; iterations: 1; fixed workload: `73e3c08f5f6cb1353c89266ff0ba73f318c2b800aa45ec3e69370c0a74537160`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `query_elements = hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim`; `key_value_elements = (hidden_states.shape[0] * hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[0] * encoder_hidden_states.shape[1]) * attn.kv_inner_dim`; `cross_attention = int(encoder_hidden_states is not None)` | 6.13714% | success |
