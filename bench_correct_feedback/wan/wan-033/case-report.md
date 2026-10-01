# wan-033 full-feedback result

Status: `success`; iterations: 6; fixed workload: `a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `batch_size = batch_size`; `padded_tokens = batch_size * max_sequence_length`; `attention_elements = batch_size * max_sequence_length ** 2`; `position_pairs = max_sequence_length ** 2` | - | invalid |
| 2 | `batch_size = batch_size`; `padded_tokens = batch_size * max_sequence_length`; `attention_elements = batch_size * max_sequence_length ** 2`; `prompt_characters = sum((len(text) for text in prompt))` | 18.3433% | retry |
| 3 | `batch_size = batch_size`; `padded_tokens = batch_size * max_sequence_length`; `prompt_characters = sum((len(text) for text in prompt))`; `loaded_modules = len(__import__('sys').modules)` | 19.627% | retry |
| 4 | `batch_size = batch_size`; `padded_tokens = batch_size * max_sequence_length`; `prompt_characters = sum((len(text) for text in prompt))`; `encoder_state_size = len(self.text_encoder.__dict__) + len(self.text_encoder.encoder.__dict__)` | 19.4506% | retry |
| 5 | `batch_size = batch_size`; `padded_tokens = batch_size * max_sequence_length`; `prompt_characters = sum((len(text) for text in prompt))`; `source_cache_entries = len(__import__('sys').modules['linecache'].cache) if 'linecache' in __import__('sys').modules else 0` | 19.321% | retry |
| 6 | `batch_size = batch_size`; `padded_tokens = batch_size * max_sequence_length` | 8.94715% | success |
