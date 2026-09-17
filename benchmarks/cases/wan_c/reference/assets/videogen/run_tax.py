"""Drive a tiny, randomly-initialised Wan 2.1 T2V pipeline (diffusers `WanPipeline`)
on CPU so the HOST-side orchestration of a video diffusion pipeline can be measured.

No downloads: the transformer / VAE / scheduler are built from configs in this file
and the text encoder is bypassed by passing precomputed `prompt_embeds` of the right
shape (so no tokenizer and no UMT5 weights are needed).

    .venv/bin/python run_tax.py [frames=9] [steps=4] [height=256] [width=256] [hw=0] [batch=1] [text=64]

Markers live in the marked COPY of the diffusers package at
/home/ubuntu/drperf-cases/videogen/wan-tax/diffusers (see mark_wan.py); this
script puts wan-tax first on sys.path itself, so the editable checkout at
./diffusers stays pristine.

Under drperf (from /home/ubuntu/drperf-cases/videogen):

    /home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \\
        --max-slots 2097152 -o out/videogen_tax --state frames=5,9,17 --state steps=4,6,8 \\
        --state hw=128,192,256 \\
        -- /home/ubuntu/drperf-cases/videogen/.venv/bin/python run_tax.py
    /home/ubuntu/drperf/bin/drperf-dev derive out/videogen_tax
    /home/ubuntu/drperf/bin/drperf-dev learn  out/videogen_tax
"""

import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import perfmark  # noqa: E402

st = perfmark.states(frames=9, steps=4, height=256, width=256, hw=0, batch=1, text=64, calls=1, sweep=0, seed=0)
FRAMES = int(st["frames"])
STEPS = int(st["steps"])
HEIGHT = int(st["height"])
WIDTH = int(st["width"])
if int(st["hw"]):                    # one grid knob for a square frame
    HEIGHT = WIDTH = int(st["hw"])
BATCH = int(st["batch"])
TEXT_LEN = int(st["text"])          # text-encoder sequence length (512 in the real pipeline)
CALLS = int(st["calls"])
SWEEP = int(st["sweep"])            # 1: several shapes in ONE process, for `drperf learn`
SEED = int(st["seed"])

import torch  # noqa: E402

torch.set_grad_enabled(False)

# the marked copy wins over the editable checkout
_SRC = "/home/ubuntu/drperf-cases/videogen/wan-tax"
sys.path.insert(0, _SRC)

import diffusers  # noqa: E402
from diffusers import AutoencoderKLWan, FlowMatchEulerDiscreteScheduler, WanPipeline, WanTransformer3DModel  # noqa: E402

if os.path.dirname(os.path.abspath(diffusers.__file__)) != os.path.join(_SRC, "diffusers"):
    sys.exit("run_tax.py: diffusers imported from %s, not the marked copy %s/diffusers"
             % (diffusers.__file__, _SRC))

# ------------------------------------------------------------------ tiny model
# Wan 2.1 T2V-1.3B for reference: patch_size (1,2,2), 12 heads x 128, in/out 16,
# text_dim 4096, freq_dim 256, ffn_dim 8960, 30 layers.  Everything below keeps
# the same *shape of the computation* (same modules, same loops) at ~1/500 the
# width so a whole pipeline call runs on CPU in a few seconds.
TEXT_DIM = 32

TRANSFORMER_CONFIG = dict(
    patch_size=(1, 2, 2),
    num_attention_heads=4,
    attention_head_dim=16,          # inner_dim = 64
    in_channels=16,
    out_channels=16,
    text_dim=TEXT_DIM,
    freq_dim=32,
    ffn_dim=128,
    num_layers=2,
    cross_attn_norm=True,
    qk_norm="rms_norm_across_heads",
    eps=1e-6,
    rope_max_seq_len=1024,
)

VAE_CONFIG = dict(
    base_dim=8,                     # 96 in the real VAE
    z_dim=16,
    dim_mult=[1, 2, 4, 4],          # -> scale_factor_spatial 8, as in the real VAE
    num_res_blocks=1,               # 2 in the real VAE
    attn_scales=[],
    temperal_downsample=[False, True, True],   # -> scale_factor_temporal 4
    scale_factor_temporal=4,
    scale_factor_spatial=8,
)


def build_pipeline():
    torch.manual_seed(SEED)
    transformer = WanTransformer3DModel(**TRANSFORMER_CONFIG).eval()
    vae = AutoencoderKLWan(**VAE_CONFIG).eval()
    scheduler = FlowMatchEulerDiscreteScheduler(shift=3.0)
    pipe = WanPipeline(
        tokenizer=None,
        text_encoder=None,
        vae=vae,
        transformer=transformer,
        scheduler=scheduler,
    )
    pipe.set_progress_bar_config(disable=True)
    return pipe


pipe = build_pipeline()
nparam = sum(p.numel() for p in pipe.transformer.parameters()) + sum(p.numel() for p in pipe.vae.parameters())

# Late attach (`drperf run --late`): DynamoRIO attaches at the first marker, so
# model construction above runs natively.  Stateless on purpose: the first
# trigger of a late-attached run is recorded without its states.
with perfmark.region("attach"):
    pass

g = torch.Generator().manual_seed(SEED)
prompt_embeds = torch.randn(BATCH, TEXT_LEN, TEXT_DIM, generator=g)
negative_prompt_embeds = torch.randn(BATCH, TEXT_LEN, TEXT_DIM, generator=g)

# `drperf learn` looks for relations between states inside ONE trace, so the
# states have to vary within the process; sweep=1 calls the pipeline at several
# shapes in a row instead of once.
SHAPES = ([(FRAMES, STEPS, HEIGHT, WIDTH)] * CALLS if not SWEEP else
          [(5, 4, 128, 128), (9, 4, 128, 128), (9, 6, 192, 192),
           (17, 6, 192, 192), (17, 8, 256, 256)])

times = []
for frames, steps, height, width in SHAPES:
    t0 = time.time()
    out = pipe(
        prompt_embeds=prompt_embeds,
        negative_prompt_embeds=negative_prompt_embeds,
        height=height,
        width=width,
        num_frames=frames,
        num_inference_steps=steps,
        guidance_scale=5.0,                       # > 1 -> CFG runs (2 transformer calls/step)
        generator=torch.Generator().manual_seed(SEED),
        output_type="np",
    )
    times.append(time.time() - t0)

video = out.frames
print("wan tiny: batch=%d text=%d params=%.2fM shapes=%s last video=%s" %
      (BATCH, TEXT_LEN, nparam / 1e6, SHAPES, getattr(video, "shape", type(video))))
print("wall per pipeline call: " + ", ".join("%.2fs" % t for t in times))
