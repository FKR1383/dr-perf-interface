"""Drive the tiny Wan 2.1 pipeline against the PROMPT-ENCODING markers (mark_t5.py).

Derived from run_more.py; imports diffusers from `videogen/wan-t5`.

    mode=0  t2v     full pipeline call with pre-computed prompt_embeds.
    mode=3  prompt  full pipeline from a real prompt: a tiny UMT5EncoderModel and
                    a duck-typed tokenizer, so the prompt path AND the
                    transformer's cross-attention (kv_len = max_sequence_length)
                    are measured in one run.
    mode=6  t5      encode_prompt only (positive + negative), REPS times in one
                    process.  `rtok` sets the number of REAL tokens per prompt,
                    `maxlen` the padding, `batch` the number of prompts.

    .venv/bin/python run_t5.py [mode=6] [rtok=32] [maxlen=512] [batch=1] [reps=3]

Under drperf (from /home/ubuntu/drperf-cases/videogen):

    /home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 \\
        --repeat 2 --max-slots 2097152 -o out/videogen_t5_sq \\
        --state mode=6 --state rtok=8,32,128,480 --state maxlen=64,128,256,512 \\
        --state batch=1,2 \\
        -- /home/ubuntu/drperf-cases/videogen/.venv/bin/python run_t5.py
"""

import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import perfmark  # noqa: E402

st = perfmark.states(frames=9, steps=4, height=256, width=256, hw=0, batch=1, text=64,
                     heads=4, mode=6, out=0, cb=0, maxlen=512, rtok=32, seed=0, reps=3,
                     tlayers=4)
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
MAXLEN = int(st["maxlen"])
RTOK = int(st["rtok"])               # real tokens per prompt (before truncation)
SEED = int(st["seed"])
REPS = int(st["reps"])
TLAYERS = int(st["tlayers"])

import torch  # noqa: E402

torch.set_grad_enabled(False)
torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "8")))

_SRC = "/home/ubuntu/drperf-cases/videogen/wan-t5"
sys.path.insert(0, _SRC)

import diffusers  # noqa: E402
from diffusers import AutoencoderKLWan, FlowMatchEulerDiscreteScheduler, WanPipeline, WanTransformer3DModel  # noqa: E402

if os.path.dirname(os.path.abspath(diffusers.__file__)) != os.path.join(_SRC, "diffusers"):
    sys.exit("run_t5.py: diffusers imported from %s, not the marked copy %s/diffusers"
             % (diffusers.__file__, _SRC))

TEXT_DIM = 32                        # == transformer text_dim, so the encoder's output
INNER_DIM = 64                       # can be fed straight to the transformer

TRANSFORMER_CONFIG = dict(
    patch_size=(1, 2, 2), num_attention_heads=HEADS, attention_head_dim=INNER_DIM // HEADS,
    in_channels=16, out_channels=16, text_dim=TEXT_DIM, freq_dim=32, ffn_dim=128,
    num_layers=2, cross_attn_norm=True, qk_norm="rms_norm_across_heads", eps=1e-6,
    rope_max_seq_len=1024,
)
VAE_CONFIG = dict(
    base_dim=8, z_dim=16, dim_mult=[1, 2, 4, 4], num_res_blocks=1, attn_scales=[],
    temperal_downsample=[False, True, True], scale_factor_temporal=4, scale_factor_spatial=8,
)


class DuckTokenizer:
    """Just enough of a T5 tokenizer for `WanPipeline._get_t5_prompt_embeds`.

    One token per whitespace-separated piece plus `</s>`, truncated at
    `max_length`, right-padded to `max_length` with mask 0 -- the same shape
    contract the real 256k-piece sentencepiece tokenizer has, which cannot be
    built offline.
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
        vocab_size=256, d_model=TEXT_DIM, d_kv=8, d_ff=64, num_layers=TLAYERS,
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
    pipe = WanPipeline(tokenizer=tokenizer, text_encoder=text_encoder, vae=vae,
                       transformer=transformer, scheduler=scheduler)
    pipe.set_progress_bar_config(disable=True)
    return pipe


PROMPT_WORDS = ("a cat and a dog baking a cake together in a cozy kitchen while "
                "sunlight streams through the window and flour drifts in the air "
                "over a wooden table covered in mixing bowls and measuring spoons ").split()

NEG = "blurry, low quality, static"          # 4 pieces -> 5 real tokens, at every maxlen


def make_prompt(words):
    """A prompt with the shape of a real one: repeated vocabulary, an HTML entity
    and doubled spaces, so basic_clean/whitespace_clean have work to do.  The
    entity is `&amp;`, which cleans to `&` INSIDE a piece, so the number of
    whitespace-separated pieces -- and therefore the real token count -- is the
    same before and after `prompt_clean`."""
    body = " ".join(PROMPT_WORDS[i % len(PROMPT_WORDS)] for i in range(words))
    return "  " + body.replace(" a ", " a&amp; ", 1) + "  "


pipe = build_pipeline(with_text=(MODE in (3, 6)))
nparam = sum(p.numel() for p in pipe.transformer.parameters()) + sum(p.numel() for p in pipe.vae.parameters())
tparam = sum(p.numel() for p in pipe.text_encoder.parameters()) if pipe.text_encoder is not None else 0

# Warm up with the markers disabled: the first encoder call in a process pays
# MKL/VML initialisation and every lazy allocation, ~2.3M instructions, and with
# `--late` it is also where DynamoRIO would attach.  Swap `perfmark.region` for a
# null context manager (the pipeline looks the attribute up at call time), run one
# call at the shapes the measured loop will use, then restore.
class _NullRegion:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


if MODE in (3, 6):
    _real_region = perfmark.region
    perfmark.region = _NullRegion
    try:
        _w = [make_prompt(RTOK - 1) for _ in range(BATCH)]
        pipe.encode_prompt(prompt=_w, negative_prompt=[NEG for _ in range(BATCH)],
                           do_classifier_free_guidance=True, max_sequence_length=MAXLEN)
    finally:
        perfmark.region = _real_region

with perfmark.region("attach"):
    pass

g = torch.Generator().manual_seed(SEED)
OUT_TYPES = {0: "np", 1: "pil", 2: "pt", 3: "latent"}

t0 = time.time()

if MODE == 0:
    prompt_embeds = torch.randn(BATCH, TEXT_LEN, TEXT_DIM, generator=g)
    negative_prompt_embeds = torch.randn(BATCH, TEXT_LEN, TEXT_DIM, generator=g)
    out = pipe(prompt_embeds=prompt_embeds, negative_prompt_embeds=negative_prompt_embeds,
               height=HEIGHT, width=WIDTH, num_frames=FRAMES, num_inference_steps=STEPS,
               guidance_scale=5.0, generator=torch.Generator().manual_seed(SEED),
               output_type=OUT_TYPES[OUT])
    res = getattr(out.frames, "shape", type(out.frames))

elif MODE == 3:
    prompts = [make_prompt(RTOK - 1) for _ in range(BATCH)]
    negs = [NEG for _ in range(BATCH)]
    out = pipe(prompt=prompts, negative_prompt=negs, height=HEIGHT, width=WIDTH,
               num_frames=FRAMES, num_inference_steps=STEPS, guidance_scale=5.0,
               max_sequence_length=MAXLEN, generator=torch.Generator().manual_seed(SEED),
               output_type=OUT_TYPES[OUT])
    res = getattr(out.frames, "shape", type(out.frames))

elif MODE == 6:
    # encode_prompt only.  Two triggers per iteration: the positive prompt at
    # rtok = batch*min(RTOK, maxlen) and the negative at rtok = batch*5, so every
    # (maxlen, batch) point carries two very different real-token counts.
    prompts = [make_prompt(RTOK - 1) for _ in range(BATCH)]
    negs = [NEG for _ in range(BATCH)]
    for _ in range(REPS):
        pe, ne = pipe.encode_prompt(prompt=prompts, negative_prompt=negs,
                                    do_classifier_free_guidance=True,
                                    max_sequence_length=MAXLEN)
    # the declared `rtok` state is computed from the UNCLEANED prompt; assert it
    # is what the tokenizer actually produced from the CLEANED one.
    from diffusers.pipelines.wan.pipeline_wan import _pm_rtok, prompt_clean
    for raw in (prompts, negs):
        want = _pm_rtok(raw, MAXLEN)
        got = int(pipe.tokenizer([prompt_clean(u) for u in raw], padding="max_length",
                                 max_length=MAXLEN)["attention_mask"].sum())
        if want != got:
            sys.exit("run_t5.py: declared rtok=%d but tokenizer produced %d" % (want, got))
    res = (tuple(pe.shape), tuple(ne.shape), _pm_rtok(prompts, MAXLEN), _pm_rtok(negs, MAXLEN))

else:
    sys.exit("run_t5.py: unknown mode %d" % MODE)

print("wan t5: mode=%d batch=%d maxlen=%d rtok=%d reps=%d tlayers=%d frames=%d steps=%d "
      "hw=%dx%d params=%.2fM tparams=%.3fM -> %s"
      % (MODE, BATCH, MAXLEN, RTOK, REPS, TLAYERS, FRAMES, STEPS, HEIGHT, WIDTH,
         nparam / 1e6, tparam / 1e6, res))
print("wall: %.2fs" % (time.time() - t0))
