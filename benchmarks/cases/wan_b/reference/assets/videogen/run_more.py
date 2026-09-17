"""Drive the tiny Wan 2.1 pipeline against the SECOND round of markers (mark_more.py).

Derived from run_tiny.py; the only differences are that it imports diffusers from
`videogen/wan-more` (mark_wan.py's 20 regions + mark_more.py's 24) and that it has
modes for the paths the first round never entered:

    mode=0  t2v     full pipeline call (default).  `out` picks output_type,
                    `cb` turns callback_on_step_end on, `heads` varies the head count.
    mode=1  enc     vae.encode() on a random video: the encode path and
                    DiagonalGaussianDistribution.
    mode=2  tile    vae.enable_tiling() then decode + encode: tiled_decode /
                    tiled_encode and their blend_v / blend_h row loops.
    mode=3  prompt  the real encode_prompt path: a tiny UMT5EncoderModel and a
                    duck-typed tokenizer, so prompt_clean (ftfy + regex), the
                    encoder call and the pad/slice/re-pad are measured.

    .venv/bin/python run_more.py [frames=9] [steps=4] [hw=256] [batch=1] [text=64]
                                 [heads=4] [mode=0] [out=0] [cb=0] [tmin=256]
                                 [tstride=192] [maxlen=64] [words=24]

Under drperf (from /home/ubuntu/drperf-cases/videogen):

    /home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \\
        --max-slots 2097152 -o out/videogen_more --state hw=128,192,256 --state frames=5,9,17 \\
        -- /home/ubuntu/drperf-cases/videogen/.venv/bin/python run_more.py
"""

import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import perfmark  # noqa: E402

st = perfmark.states(frames=9, steps=4, height=256, width=256, hw=0, batch=1, text=64,
                     heads=4, mode=0, out=0, cb=0, tmin=256, tstride=192, maxlen=64,
                     words=24, seed=0)
FRAMES = int(st["frames"])
STEPS = int(st["steps"])
HEIGHT = int(st["height"])
WIDTH = int(st["width"])
if int(st["hw"]):
    HEIGHT = WIDTH = int(st["hw"])
BATCH = int(st["batch"])
TEXT_LEN = int(st["text"])
HEADS = int(st["heads"])
MODE = int(st["mode"])
OUT = int(st["out"])                 # 0 np, 1 pil, 2 pt, 3 latent
CB = int(st["cb"])
TMIN = int(st["tmin"])
TSTRIDE = int(st["tstride"])
MAXLEN = int(st["maxlen"])
WORDS = int(st["words"])
SEED = int(st["seed"])

import torch  # noqa: E402

torch.set_grad_enabled(False)
torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "8")))

_SRC = "/home/ubuntu/drperf-cases/videogen/wan-more"
sys.path.insert(0, _SRC)

import diffusers  # noqa: E402
from diffusers import AutoencoderKLWan, FlowMatchEulerDiscreteScheduler, WanPipeline, WanTransformer3DModel  # noqa: E402

if os.path.dirname(os.path.abspath(diffusers.__file__)) != os.path.join(_SRC, "diffusers"):
    sys.exit("run_more.py: diffusers imported from %s, not the marked copy %s/diffusers"
             % (diffusers.__file__, _SRC))

TEXT_DIM = 32
INNER_DIM = 64                       # kept fixed while `heads` varies

TRANSFORMER_CONFIG = dict(
    patch_size=(1, 2, 2),
    num_attention_heads=HEADS,
    attention_head_dim=INNER_DIM // HEADS,
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
    base_dim=8,
    z_dim=16,
    dim_mult=[1, 2, 4, 4],
    num_res_blocks=1,
    attn_scales=[],
    temperal_downsample=[False, True, True],
    scale_factor_temporal=4,
    scale_factor_spatial=8,
)


# ----------------------------------------------------------- tiny text encoder
class DuckTokenizer:
    """Just enough of a T5 tokenizer for `WanPipeline._get_t5_prompt_embeds`.

    The real tokenizer is a 256k-piece sentencepiece model that cannot be built
    offline; the pipeline only reads `.input_ids` and `.attention_mask` from what
    it returns, and every host-side cost after it (the encoder call, the slice,
    the re-pad, the repeat) depends on `max_length` and on how many tokens are
    unmasked, both of which this reproduces.
    """

    class Out(dict):
        @property
        def input_ids(self):
            return self["input_ids"]

        @property
        def attention_mask(self):
            return self["attention_mask"]

    def __init__(self, vocab_size):
        self.vocab_size = vocab_size

    def __call__(self, prompt, padding=None, max_length=None, truncation=None,
                 add_special_tokens=None, return_attention_mask=None, return_tensors=None):
        prompts = [prompt] if isinstance(prompt, str) else list(prompt)
        b = len(prompts)
        ids = torch.zeros(b, max_length, dtype=torch.long)
        mask = torch.zeros(b, max_length, dtype=torch.long)
        for i, p in enumerate(prompts):
            n = min(len(p.split()) + 1, max_length)     # +1 for </s>
            ids[i, :n] = torch.arange(1, n + 1) % self.vocab_size
            mask[i, :n] = 1
        return self.Out(input_ids=ids, attention_mask=mask)


def build_text_encoder():
    from transformers import UMT5Config, UMT5EncoderModel
    cfg = UMT5Config(
        vocab_size=256, d_model=TEXT_DIM, d_kv=8, d_ff=64, num_layers=1,
        num_heads=4, relative_attention_num_buckets=8, dropout_rate=0.0,
    )
    torch.manual_seed(SEED)
    return UMT5EncoderModel(cfg).eval(), DuckTokenizer(cfg.vocab_size)


def build_pipeline(with_text=False):
    torch.manual_seed(SEED)
    transformer = WanTransformer3DModel(**TRANSFORMER_CONFIG).eval()
    vae = AutoencoderKLWan(**VAE_CONFIG).eval()
    scheduler = FlowMatchEulerDiscreteScheduler(shift=3.0)
    text_encoder, tokenizer = build_text_encoder() if with_text else (None, None)
    pipe = WanPipeline(
        tokenizer=tokenizer,
        text_encoder=text_encoder,
        vae=vae,
        transformer=transformer,
        scheduler=scheduler,
    )
    pipe.set_progress_bar_config(disable=True)
    return pipe


PROMPT_WORDS = ("a cat and a dog baking a cake together in a cozy kitchen while "
                "sunlight streams through the window and flour drifts in the air "
                "over a wooden table covered in mixing bowls and measuring spoons ").split()


def make_prompt(words):
    # a prompt with the shape of a real one: repeated vocabulary, an HTML entity
    # and a doubled space, so basic_clean/whitespace_clean have work to do.
    body = " ".join(PROMPT_WORDS[i % len(PROMPT_WORDS)] for i in range(words))
    return "  " + body.replace(" a ", " a&nbsp;", 1) + "  "


pipe = build_pipeline(with_text=(MODE == 3))
nparam = sum(p.numel() for p in pipe.transformer.parameters()) + sum(p.numel() for p in pipe.vae.parameters())

with perfmark.region("attach"):
    pass

g = torch.Generator().manual_seed(SEED)
OUT_TYPES = {0: "np", 1: "pil", 2: "pt", 3: "latent"}


def _cb(pipeline, i, t, kwargs):
    return {}


t0 = time.time()

if MODE == 0:
    prompt_embeds = torch.randn(BATCH, TEXT_LEN, TEXT_DIM, generator=g)
    negative_prompt_embeds = torch.randn(BATCH, TEXT_LEN, TEXT_DIM, generator=g)
    kw = {}
    if CB:
        kw["callback_on_step_end"] = _cb
        kw["callback_on_step_end_tensor_inputs"] = (
            ["latents", "prompt_embeds", "negative_prompt_embeds"][:CB]
        )
    out = pipe(
        prompt_embeds=prompt_embeds,
        negative_prompt_embeds=negative_prompt_embeds,
        height=HEIGHT, width=WIDTH, num_frames=FRAMES,
        num_inference_steps=STEPS, guidance_scale=5.0,
        generator=torch.Generator().manual_seed(SEED),
        output_type=OUT_TYPES[OUT],
        **kw
    )
    res = getattr(out.frames, "shape", type(out.frames))

elif MODE == 1:
    video = torch.randn(BATCH, 3, FRAMES, HEIGHT, WIDTH, generator=g)
    post = pipe.vae.encode(video).latent_dist
    res = tuple(post.mode().shape)

elif MODE == 2:
    pipe.vae.enable_tiling(tile_sample_min_height=TMIN, tile_sample_min_width=TMIN,
                           tile_sample_stride_height=TSTRIDE, tile_sample_stride_width=TSTRIDE)
    lat_f = (FRAMES - 1) // 4 + 1
    z = torch.randn(BATCH, 16, lat_f, HEIGHT // 8, WIDTH // 8, generator=g)
    dec = pipe.vae.decode(z, return_dict=False)[0]
    video = torch.randn(BATCH, 3, FRAMES, HEIGHT, WIDTH, generator=g)
    enc = pipe.vae.encode(video).latent_dist.mode()
    res = (tuple(dec.shape), tuple(enc.shape))

elif MODE == 3:
    prompts = [make_prompt(WORDS) for _ in range(BATCH)]
    negs = ["blurry, low quality, static" for _ in range(BATCH)]
    out = pipe(
        prompt=prompts, negative_prompt=negs,
        height=HEIGHT, width=WIDTH, num_frames=FRAMES,
        num_inference_steps=STEPS, guidance_scale=5.0,
        max_sequence_length=MAXLEN,
        generator=torch.Generator().manual_seed(SEED),
        output_type=OUT_TYPES[OUT],
    )
    res = getattr(out.frames, "shape", type(out.frames))

else:
    sys.exit("run_more.py: unknown mode %d" % MODE)

print("wan more: mode=%d frames=%d steps=%d hw=%dx%d batch=%d text=%d heads=%d out=%s "
      "cb=%d tmin=%d tstride=%d maxlen=%d words=%d params=%.2fM -> %s"
      % (MODE, FRAMES, STEPS, HEIGHT, WIDTH, BATCH, TEXT_LEN, HEADS, OUT_TYPES[OUT],
         CB, TMIN, TSTRIDE, MAXLEN, WORDS, nparam / 1e6, res))
print("wall: %.2fs" % (time.time() - t0))
