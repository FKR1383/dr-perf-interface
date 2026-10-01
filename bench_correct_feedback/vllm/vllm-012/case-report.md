# vllm-012 full-feedback result

Status: `success`; iterations: 3; fixed workload: `e1acd78660be84b1b47a6d96d8d4c03c5fdd651749ce9623fed34c26dd704977`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `lookup_enabled = int(self.enable_caching and (not request.skip_reading_prefix_cache))`; `has_lookup_blocks = int(self.enable_caching and (not request.skip_reading_prefix_cache) and (min(len(request.block_hashes), (request.num_tokens - 1) // self.kv_cache_config.kv_cache_groups[0].kv_cache_spec.block_size) > 0))`; `first_block_cached = int(self.enable_caching and (not request.skip_reading_prefix_cache) and bool(request.block_hashes) and (request.block_hashes[0] + b'\x00\x00\x00\x00' in self.block_pool.cached_block_hash_to_block._cache))`; `cached_prefix_search_extent = min(len(request.block_hashes), (request.num_tokens - 1) // self.kv_cache_config.kv_cache_groups[0].kv_cache_spec.block_size) if self.enable_caching and (not request.skip_reading_prefix_cache) and request.block_hashes and (request.block_hashes[0] + b'\x00\x00\x00\x00' in self.block_pool.cached_block_hash_to_block._cache) else 0` | - | invalid |
| 2 | `request_tokens = request.num_tokens` | 27.7718% | retry |
| 3 | `request_tokens = request.num_tokens`; `ten_token_prompt = int(request.num_tokens == 10)`; `eleven_token_prompt = int(request.num_tokens == 11)` | 0% | success |
