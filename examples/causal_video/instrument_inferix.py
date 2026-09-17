"""drperf regions for Inferix Self-Forcing; PCVs use host-readable metadata only.

Install after warmup. Region names are shared across layers; ``layer`` is a string diagnostic
state, not a numeric PCV or another axis of the fitting key. No tensor values
are copied to the host to construct PCVs.
"""

import functools
import inspect


def install(pipe):
    import perfmark
    from inferix.kvcache_manager.kvcache_manager import KVCacheManager
    from inferix.kvcache_manager.model.self_forcing_kv_cache_manager import SelfForcingKVCacheManager
    from inferix.models.self_forcing import causal_model
    from inferix.models.wan_base import model as wan_model, vae
    from inferix.pipeline.self_forcing.CausalInferencePipeline import CausalInferencePipeline

    if hasattr(pipe, "_perfmark_inferix_regions"):
        return pipe._perfmark_inferix_regions

    blocks = tuple(pipe.pipeline.generator.model.blocks)
    layer_of = {}
    for index, block in enumerate(blocks):
        layer_of[id(block)] = index
        layer_of[id(block.self_attn)] = index
        layer_of[id(block.cross_attn)] = index
    regions = []

    def shape(x, axis):
        if isinstance(x, (list, tuple)):
            return shape(x[0], axis) if x else 0
        return int(x.shape[axis]) if x is not None else 0

    def value(arguments, name, position=0):
        if name in arguments:
            return arguments[name]
        if name in arguments.get("kwargs", {}):
            return arguments["kwargs"][name]
        positional = arguments.get("args", ())
        return positional[position] if len(positional) > position else None

    def layer(arguments):
        obj = arguments["self"]
        return str(layer_of.get(id(obj), getattr(obj, "layer_number", -1)))

    def tokens(arguments):
        x = value(arguments, "x")
        return {"tokens": shape(x, 1)}

    def layer_tokens(arguments):
        return {"layer": layer(arguments), **tokens(arguments)}

    def attention(arguments):
        return {"layer": layer(arguments), "tokens": shape(value(arguments, "x"), 1),
                "context_tokens": shape(value(arguments, "context", 1), 1)}

    def self_attention(arguments):
        x = value(arguments, "x")
        current_start = value(arguments, "current_start")
        # current_start is a Python integer in the single-GPU inference path.
        # Never convert a GPU tensor to a host scalar for a PCV.
        prefix = current_start if isinstance(current_start, int) else 0
        return {"layer": layer(arguments), "tokens": shape(x, 1),
                "context_tokens": prefix + shape(x, 1)}

    def wrap(owner, method, name, features):
        original = getattr(owner, method)
        signature = inspect.signature(original)

        @functools.wraps(original)
        def measured(*args, **kwargs):
            arguments = signature.bind_partial(*args, **kwargs).arguments
            with perfmark.region(name, **features(arguments)):
                return original(*args, **kwargs)

        setattr(owner, method, measured)
        regions.append(name)

    # One inference region is enough for the outer path; runner phases retain
    # the larger public generation interval without another drperf parent.
    wrap(CausalInferencePipeline, "inference", "inferix_inference",
         lambda a: {"frames": shape(a.get("noise"), 1),
                    "initial_frames": shape(a.get("initial_latent"), 1),
                    "batch": shape(a.get("noise"), 0)})
    # The runner installs host-phase wrappers on these three *instances*
    # before warmup. Wrap those active call paths, not their class methods.
    wrap(pipe.pipeline.text_encoder, "forward", "inferix_text_encode",
         lambda a: {"prompts": len(value(a, "text_prompts") or ())})
    wrap(pipe.pipeline.generator, "forward", "inferix_generator",
         lambda a: {"frames": shape(value(a, "noisy_image_or_video"), 1),
                    "batch": shape(value(a, "noisy_image_or_video"), 0)})
    wrap(causal_model.CausalWanModel, "_forward_inference", "inferix_transformer",
         lambda a: {"frames": shape(a.get("x"), 1),
                    "batch": len(a["x"]) if isinstance(a.get("x"), (list, tuple)) else shape(a.get("x"), 0),
                    "layers": len(blocks)})
    wrap(causal_model.CausalWanAttentionBlock, "forward", "inferix_block", layer_tokens)
    wrap(causal_model.CausalWanSelfAttention, "forward", "inferix_self_attention", self_attention)
    for cls in (wan_model.WanT2VCrossAttention, wan_model.WanI2VCrossAttention):
        wrap(cls, "forward", "inferix_cross_attention", attention)
    wrap(causal_model, "causal_rope_apply", "inferix_causal_rope",
         lambda a: {"tokens": shape(a.get("x"), 1),
                    "heads": shape(a.get("x"), 2)})
    wrap(causal_model, "causal_rope_apply_chunked", "inferix_causal_rope_chunked",
         lambda a: {"tokens": shape(a.get("x"), 1),
                    "world_size": int(a.get("world_size", 1))})
    wrap(causal_model, "rope_apply", "inferix_rope", tokens)

    wrap(pipe.pipeline.vae, "decode_to_pixel", "inferix_vae_decode_to_pixel",
         lambda a: {"frames": shape(value(a, "latent"), 1),
                    "batch": shape(value(a, "latent"), 0),
                    "cached": int(bool(value(a, "use_cache") or False))})
    wrap(vae.WanVAE_, "decode", "inferix_vae_decode",
         lambda a: {"frames": shape(a.get("z"), 2)})
    wrap(vae.WanVAE_, "cached_decode", "inferix_vae_cached_decode",
         lambda a: {"frames": shape(a.get("z"), 2)})
    wrap(vae.Decoder3d, "forward", "inferix_vae_decoder",
         lambda a: {"frames": shape(a.get("x"), 2)})
    wrap(vae.WanVAE_, "clear_cache", "inferix_vae_clear_cache", lambda a: {})

    wrap(KVCacheManager, "allocate_slots", "inferix_kv_allocate_slots",
         lambda a: {"tokens": int(a["spec"].num_tokens),
                    "layers": len(a["spec"].specs)})
    wrap(KVCacheManager, "free", "inferix_kv_free", lambda a: {})
    wrap(SelfForcingKVCacheManager, "get_kv_cache", "inferix_kv_get",
         lambda a: {"layer": layer(a)})
    wrap(SelfForcingKVCacheManager, "set_kv_cache", "inferix_kv_set",
         lambda a: {"layer": layer(a), "cache_tokens": shape(a.get("k_data"), 0)})
    wrap(SelfForcingKVCacheManager, "get_crossattn_cache", "inferix_cross_kv_get",
         lambda a: {"layer": layer(a)})
    wrap(SelfForcingKVCacheManager, "set_crossattn_cache", "inferix_cross_kv_set",
         lambda a: {"layer": layer(a), "cache_tokens": shape(a.get("k_data"), 0)})

    pipe._perfmark_inferix_regions = list(dict.fromkeys(regions))
    return pipe._perfmark_inferix_regions
