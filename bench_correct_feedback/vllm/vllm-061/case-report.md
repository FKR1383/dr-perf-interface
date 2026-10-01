# vllm-061 full-feedback result

Status: `success`; iterations: 3; fixed workload: `399da689197cc16ffaca73281333878aac35304057e6e7648a84e503296af96f`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `copied_token_count = (len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0) + len(request.output_token_ids)`; `block_count = sum((len(block_ids) for block_ids in request.block_ids))`; `random_sampling = int(request.sampling_params is not None and request.sampling_params.temperature != 0.0)`; `penalty_count = int(request.sampling_params.frequency_penalty != 0.0) + int(request.sampling_params.presence_penalty != 0.0) + int(request.sampling_params.repetition_penalty != 1.0) if request.sampling_params is not None else 0` | 43.0098% | retry |
| 2 | `copied_token_count = (len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0) + len(request.output_token_ids)`; `resident_requests = len(self.req_id_to_index)`; `removed_slots = len(self.batch_update_builder.removed)`; `uncached_sampling_type = int(request.sampling_params is not None and 'sampling_type' not in request.sampling_params.__dict__)` | 44.7386% | retry |
| 3 | `copied_token_count = (len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0) + len(request.output_token_ids)`; `short_prompt = int(request.num_prompt_tokens <= 11)`; `short_prompt_empty_batch = int(request.num_prompt_tokens <= 11 and len(self.req_id_to_index) == 0)`; `short_prompt_empty_batch_append = int(request.num_prompt_tokens <= 11 and len(self.req_id_to_index) == 0 and (len(self.batch_update_builder.removed) == 0))` | 8.02361% | success |
