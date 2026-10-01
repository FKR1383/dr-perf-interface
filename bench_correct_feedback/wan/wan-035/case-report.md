# wan-035 full-feedback result

Status: `success`; iterations: 2; fixed workload: `4feecb9cffd2264d9024147562469be33918af9922ef0218791ad864e5b41715`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `batch_size = 1 if isinstance(prompt, str) else len(prompt)`; `padded_tokens = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length`; `attention_elements = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length ** 2`; `position_pairs = max_sequence_length ** 2` | - | invalid |
| 2 | `batch_size = 1 if isinstance(prompt, str) else len(prompt)`; `padded_tokens = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length`; `prompt_characters = len(prompt) if isinstance(prompt, str) else sum((len(text) for text in prompt))` | 7.98443% | success |
