"""Shape-preserving SelfForcing metadata path, shared by native and GX runs.

Installed inside FastVideo's worker after model load and before warmup. The
normal runner path leaves upstream behavior unchanged for a reference result.
"""

from functools import wraps


def shape_based_t5_postprocess(outputs):
    """Pad a single unpadded T5 prompt without reducing its GPU mask."""
    import torch.nn.functional as functional

    hidden = outputs.last_hidden_state
    length = hidden.shape[1]
    if length > 512:
        raise ValueError(f"SelfForcing T5 token count exceeds 512: {length}")
    return functional.pad(hidden, (0, 0, 0, 512 - length))


def install(worker_proc):
    from fastvideo.pipelines.basic.wan.stages.causal_denoising import WanCausalDenoisingBase

    gpu_worker = worker_proc.worker
    args = gpu_worker.fastvideo_args
    config = args.pipeline_config
    assert len(config.postprocess_text_funcs) == 1
    assert len(config.text_encoder_configs) == 1
    padding = config.text_encoder_configs[0].tokenizer_kwargs.get("padding")
    assert padding in (None, False, "do_not_pad"), padding

    if not getattr(WanCausalDenoisingBase._initialize_kv_cache, "_metadata_mode", False):
        original = WanCausalDenoisingBase._initialize_kv_cache

        @wraps(original)
        def python_index_cache(self, batch_size, dtype, device):
            caches = original(self, batch_size, dtype, device)
            for cache in caches:
                # Cache positions determine only Python branches and slices.
                # The attention implementation already accepts Python ints.
                cache["global_end_index"] = 0
                cache["local_end_index"] = 0
            return caches

        python_index_cache._metadata_mode = True
        WanCausalDenoisingBase._initialize_kv_cache = python_index_cache

    for live_args in (args, gpu_worker.pipeline.fastvideo_args):
        live_args.pipeline_config.postprocess_text_funcs = (shape_based_t5_postprocess,)
        live_args.enable_stage_verification = False
    return ["python_kv_cache_indices", "shape_based_t5_padding", "stage_verification_disabled"]
