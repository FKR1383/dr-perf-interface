# vllm-043 full-feedback result

Status: `success`; iterations: 2; fixed workload: `0a38730cdfad33eeaa9d5b87d01cca950895dd774298495607ef82d98b826007`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `decoded_token_count = len(new_token_ids) - int(bool(new_token_ids) and stop_terminated and (not self.include_stop_str_in_output))`; `nonempty_update = int(bool(new_token_ids))`; `skipped_terminal_token = int(bool(new_token_ids) and stop_terminated and (not self.include_stop_str_in_output))` | 21.2112% | retry |
| 2 | `decoded_token_count = len(new_token_ids) - int(bool(new_token_ids) and stop_terminated and (not self.include_stop_str_in_output))`; `nonempty_update = int(bool(new_token_ids))`; `skipped_terminal_token = int(bool(new_token_ids) and stop_terminated and (not self.include_stop_str_in_output))`; `short_nonempty_batch = int(0 < len(new_token_ids) <= 2)` | 9.91274% | success |
