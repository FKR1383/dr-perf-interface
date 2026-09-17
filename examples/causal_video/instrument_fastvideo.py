"""Worker-side drperf regions for FastVideo SelfForcing inference.

Install after a full warmup. PCVs use Python values and tensor shapes only;
they never read GPU tensor contents. The first measured worker region is the
pipeline forward call, allowing late attachment to that worker process.
"""

import functools
import inspect
import os


def install(worker_proc):
    import perfmark
    from fastvideo.models.wan import causal_transformer, transformer, vae
    from fastvideo.pipelines.basic.wan.stages.causal_denoising import (
        CausalDMDDenosingStage, WanCausalDenoisingBase)
    from fastvideo.pipelines.stages.decoding import DecodingStage
    from fastvideo.pipelines.stages.text_encoding import TextEncodingStage

    gpu_worker = worker_proc.worker
    pipeline = gpu_worker.pipeline
    if hasattr(pipeline, "_perfmark_fastvideo_regions"):
        return {"pid": os.getpid(), "regions": pipeline._perfmark_fastvideo_regions}

    model = pipeline.get_module("transformer")
    blocks = tuple(model.blocks)
    layer_of = {}
    for index, block in enumerate(blocks):
        for module in (block, block.attn1, block.attn2):
            layer_of[id(module)] = index
    regions = []

    def shape(value, axis):
        return int(value.shape[axis]) if value is not None else 0

    def host_int(value):
        if not isinstance(value, int):
            raise TypeError(f"drperf PCV requires a Python int, got {type(value).__name__}")
        return value

    def layer(arguments):
        return str(layer_of.get(id(arguments.get("self")), -1))

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

    wrap(pipeline, "forward", "fastvideo_pipeline",
         lambda a: {"frames": int(a["batch"].num_frames), "batch": shape(a["batch"].latents, 0)})
    wrap(TextEncodingStage, "forward", "fastvideo_text_encode",
         lambda a: {"prompts": 1 if isinstance(a["batch"].prompt, str) else len(a["batch"].prompt)})
    wrap(CausalDMDDenosingStage, "forward", "fastvideo_causal_denoise",
         lambda a: {"latent_frames": shape(a["batch"].latents, 2),
                    "blocks": shape(a["batch"].latents, 2) // int(a["self"].num_frames_per_block),
                    "steps": len(a["fastvideo_args"].pipeline_config.dmd_denoising_steps)})
    wrap(WanCausalDenoisingBase, "_initialize_kv_cache", "fastvideo_kv_init",
         lambda a: {"batch": int(a["batch_size"]), "layers": len(blocks),
                    "capacity_tokens": int(a["self"].frame_seq_length) *
                    int(a["self"].sliding_window_num_frames)})
    wrap(WanCausalDenoisingBase, "_initialize_crossattn_cache", "fastvideo_cross_kv_init",
         lambda a: {"batch": int(a["batch_size"]), "layers": len(blocks),
                    "text_tokens": int(a["max_text_len"])})
    wrap(causal_transformer.CausalWanTransformer3DModel, "_forward_inference",
         "fastvideo_transformer",
         lambda a: {"frames": shape(a["hidden_states"], 2),
                    "batch": shape(a["hidden_states"], 0), "layers": len(blocks)})
    wrap(causal_transformer.CausalWanTransformerBlock, "forward", "fastvideo_block",
         lambda a: {"layer": layer(a), "tokens": shape(a["hidden_states"], 1)})
    wrap(causal_transformer.CausalWanSelfAttention, "forward", "fastvideo_self_attention",
         lambda a: {"layer": layer(a), "tokens": shape(a["q"], 1),
                    "context_tokens": host_int(a.get("current_start", 0)) + shape(a["q"], 1)})
    wrap(transformer.WanT2VCrossAttention, "forward", "fastvideo_cross_attention",
         lambda a: {"layer": layer(a), "tokens": shape(a["x"], 1),
                    "context_tokens": shape(a["context"], 1)})
    wrap(causal_transformer, "_apply_rotary_emb", "fastvideo_rope",
         lambda a: {"tokens": shape(a["x"], 1), "heads": shape(a["x"], 2)})
    wrap(causal_transformer, "get_rotary_pos_embed", "fastvideo_rope_tables",
         lambda a: {"frames": int(a["rope_sizes"][0]),
                    "height": int(a["rope_sizes"][1]),
                    "width": int(a["rope_sizes"][2]),
                    "head_dim": int(a["hidden_size"]) // int(a["heads_num"]),
                    "start_frame": host_int(a.get("start_frame", 0))})
    wrap(DecodingStage, "forward", "fastvideo_decode_stage",
         lambda a: {"latent_frames": shape(a["batch"].latents, 2)})
    wrap(vae.AutoencoderKLWan, "decode", "fastvideo_vae_decode",
         lambda a: {"latent_frames": shape(a["z"], 2)})
    wrap(vae.WanDecoder3d, "forward", "fastvideo_vae_decoder",
         lambda a: {"latent_frames": shape(a["x"], 2)})
    wrap(vae.AutoencoderKLWan, "clear_cache", "fastvideo_vae_clear_cache",
         lambda a: {})

    pipeline._perfmark_fastvideo_regions = list(dict.fromkeys(regions))
    return {"pid": os.getpid(), "regions": pipeline._perfmark_fastvideo_regions}
