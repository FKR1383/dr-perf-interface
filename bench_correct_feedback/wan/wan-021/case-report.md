# wan-021 full-feedback result

Status: `success`; iterations: 1; fixed workload: `c411a85c82ed43a90b1121a15763975b8e28e430eaacb0efc01d9660b911c2e1`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `rotary_output_elements = hidden_states.shape[2] // self.patch_size[0] * (hidden_states.shape[3] // self.patch_size[1]) * (hidden_states.shape[4] // self.patch_size[2]) * self.attention_head_dim`; `singleton_temporal_axis = int(hidden_states.shape[2] // self.patch_size[0] == 1)` | 1.59201% | success |
