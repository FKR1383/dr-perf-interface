"""Equivalence check for the Wan 2.1 prompt-encoding fix.

    .venv/bin/python equiv_t5.py SRC_DIR OUT.npz

Builds exactly the pipeline `run_t5.py` builds (tiny transformer + VAE + a tiny
UMT5EncoderModel and the duck-typed tokenizer, same configs and seeds) from the
diffusers package found under SRC_DIR, then for a spread of
(batch, max_sequence_length, real tokens) points records

  * prompt_embeds and negative_prompt_embeds from `encode_prompt`
  * the LATENTS of a full `pipe(prompt=...)` call (output_type="latent")
  * the decoded VIDEO tensor (output_type="pt")

into OUT.npz, and prints a sha256 of each.  `cmp_t5.py A.npz B.npz` then reports
the max absolute difference per array, so "identical" can be stated as a number.

    .venv/bin/python equiv_t5.py diffusers/src /tmp/base.npz
    .venv/bin/python equiv_t5.py wan-t5        /tmp/fix.npz
    .venv/bin/python cmp_t5.py /tmp/base.npz /tmp/fix.npz
"""

import hashlib
import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

SRC = os.path.abspath(sys.argv[1])
DST = sys.argv[2]
sys.path.insert(0, "/home/ubuntu/drperf/perfmark/python")   # marked copies import perfmark
sys.path.insert(0, SRC)

import numpy as np  # noqa: E402
import torch  # noqa: E402

torch.set_grad_enabled(False)
torch.set_num_threads(8)

import diffusers  # noqa: E402
from diffusers import AutoencoderKLWan, FlowMatchEulerDiscreteScheduler, WanPipeline, WanTransformer3DModel  # noqa: E402

got = os.path.dirname(os.path.abspath(diffusers.__file__))
if got != os.path.join(SRC, "diffusers"):
    sys.exit("equiv_t5.py: diffusers imported from %s, not %s/diffusers" % (got, SRC))

sys.path.insert(0, "/home/ubuntu/drperf-cases/videogen")
from equiv_t5_common import SEED, DuckTokenizer, NEG, build, make_prompt  # noqa: E402


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float32).tobytes()).hexdigest()[:32]


# (batch, max_sequence_length, real tokens per prompt)
POINTS = [
    (1, 512, 8), (1, 512, 32), (1, 512, 128), (1, 512, 480),
    (2, 512, 32), (2, 256, 32), (2, 128, 32), (1, 64, 8), (1, 64, 480),
    (3, 512, 9),                 # ragged: three prompts of different lengths
]

pipe = build(WanTransformer3DModel, AutoencoderKLWan,
             FlowMatchEulerDiscreteScheduler, WanPipeline)
out = {}

for bi, (batch, maxlen, rtok) in enumerate(POINTS):
    if batch == 3:
        prompts = [make_prompt(7), make_prompt(31), make_prompt(200)]
    else:
        prompts = [make_prompt(rtok - 1) for _ in range(batch)]
    negs = [NEG for _ in range(batch)]
    pe, ne = pipe.encode_prompt(prompt=prompts, negative_prompt=negs,
                                do_classifier_free_guidance=True,
                                max_sequence_length=maxlen)
    out["pe%02d" % bi] = pe.numpy()
    out["ne%02d" % bi] = ne.numpy()
    print("b=%d maxlen=%-4d rtok=%-4d  pe %s %s   ne %s"
          % (batch, maxlen, rtok, digest(pe.numpy()), tuple(pe.shape), digest(ne.numpy())))

# full pipeline: latents and decoded video
for pi, (frames, steps, hw, batch, maxlen, rtok) in enumerate(
        [(5, 4, 128, 1, 512, 32), (9, 3, 192, 2, 256, 128), (5, 2, 128, 1, 64, 480)]):
    prompts = [make_prompt(rtok - 1) for _ in range(batch)]
    negs = [NEG for _ in range(batch)]
    kw = dict(prompt=prompts, negative_prompt=negs, height=hw, width=hw,
              num_frames=frames, num_inference_steps=steps, guidance_scale=5.0,
              max_sequence_length=maxlen)
    lat = pipe(generator=torch.Generator().manual_seed(SEED), output_type="latent", **kw).frames
    vid = pipe(generator=torch.Generator().manual_seed(SEED), output_type="pt", **kw).frames
    out["lat%02d" % pi] = lat.numpy()
    out["vid%02d" % pi] = vid.numpy()
    print("frames=%-3d steps=%d hw=%-4d b=%d maxlen=%-4d rtok=%-4d  latents %s  video %s"
          % (frames, steps, hw, batch, maxlen, rtok, digest(lat.numpy()), digest(vid.numpy())))

np.savez(DST, **out)
print("wrote %s (%d arrays)" % (DST, len(out)))
