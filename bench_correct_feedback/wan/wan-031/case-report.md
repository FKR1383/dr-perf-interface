# wan-031 full-feedback result

Status: `success`; iterations: 6; fixed workload: `fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `batch_size = 1 if isinstance(prompt, str) else len(prompt)`; `token_positions = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length`; `attention_pairs = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length ** 2`; `prompt_characters = len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))` | 32.7203% | retry |
| 2 | `loaded_modules = len(__import__('sys').modules)`; `batch_size = 1 if isinstance(prompt, str) else len(prompt)`; `token_positions = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length`; `prompt_characters = len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))` | 34.1891% | retry |
| 3 | `source_cache_entries = len(__import__('sys').modules['linecache'].cache) if 'linecache' in __import__('sys').modules else 0`; `batch_size = 1 if isinstance(prompt, str) else len(prompt)`; `token_positions = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length`; `prompt_characters = len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))` | 34.2215% | retry |
| 4 | `regex_cache_entries = len(re._main._cache)`; `batch_size = 1 if isinstance(prompt, str) else len(prompt)`; `token_positions = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length`; `prompt_characters = len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))` | 12.148% | retry |
| 5 | `regex_cache_cold = int(len(re._main._cache) < 15)`; `batch_size = 1 if isinstance(prompt, str) else len(prompt)`; `token_positions = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length`; `prompt_characters = len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))` | 12.0319% | retry |
| 6 | `regex_cache_cold = int(len(re._main._cache) < 15)`; `batch_size = 1 if isinstance(prompt, str) else len(prompt)`; `token_positions = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length`; `attention_pairs = (1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length ** 2` | 3.36929% | success |
