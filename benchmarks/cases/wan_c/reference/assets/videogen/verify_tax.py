"""Trigger-count check for the wan-tax runs (baseline regions + probe sub-regions).

    python verify_tax.py out/videogen_tax_probe      # probe run: sub-regions expected
    python verify_tax.py out/videogen_tax            # marker-free run: baseline only

Same purpose as verify_regions.py: drperf's per-thread key cache compares the
region and state-name strings by POINTER (client/drperf.c:339-351), so two
regions under one root with the same state COUNT and the same state VALUES are
recorded as one key.  Every probe region here declares one state with a unique
multiplier, and this script is what checks that the separation held.
"""

import collections
import glob
import json
import os
import sys

LAYERS = 2
CFG = 2

DS = ["ds_null", "ds_setup", "ds_input", "ds_timestep", "ds_cond", "ds_uncond",
      "ds_combine", "ds_sched", "ds_callback", "ds_progress", "ds_xla"]
TF = ["tf_null", "tf_shape", "tf_rope", "tf_patch", "tf_flatten", "tf_contig", "tf_tsdim",
      "tf_cond", "tf_unflat", "tf_blocks", "tf_shift", "tf_normout", "tf_projout",
      "tf_unpatch", "tf_ret"]
BL = ["bl_null", "bl_mod", "bl_norm1", "bl_attn1", "bl_res1", "bl_norm2", "bl_attn2",
      "bl_res2", "bl_norm3", "bl_ffn", "bl_res3"]
AT = ["null", "img", "qkv", "qknorm", "unflat", "rope", "sdpa", "flat", "out"]


def expected(frames, steps, batch, probe):
    latent_frames = (frames - 1) // 4 + 1
    tf = CFG * steps
    want = {
        "attach": 1, "wan_call": 1, "encode_prompt": 1, "set_timesteps": 1,
        "prepare_latents": 1, "denoise_step": steps, "cfg": steps, "sched_step": steps,
        "transformer_forward": tf, "rope": tf, "cond_embed": tf,
        "block": tf * LAYERS, "attn": tf * LAYERS * 2,
        "vae_stage": 1, "vae_decode": 1, "vae_decode_frames": 1, "vae_clear_cache": 2,
        "vae_frame_loop": latent_frames, "vae_decode_chunk": latent_frames,
        "postprocess_video": 1, "postprocess_frames": batch,
    }
    if probe:
        want.update({r: steps for r in DS})
        want.update({r: tf for r in TF})
        want.update({r: tf * LAYERS for r in BL})
        want.update({"at_" + r: tf * LAYERS for r in AT})     # self-attention
        want.update({"ax_" + r: tf * LAYERS for r in AT})     # cross-attention
    return want


def main():
    out = sys.argv[1]
    index = json.load(open(os.path.join(out, "index.json")))
    probe = "probe" in os.path.basename(out)
    bad = 0
    for run in index["runs"]:
        state = dict(run["state"])
        frames, steps = int(state.get("frames", 9)), int(state.get("steps", 4))
        batch = int(state.get("batch", 1))
        for fname in run["files"]:
            path = os.path.join(out, fname)
            meta = json.load(open(path))["drperf"]
            trace = path + ".trace"
            if not os.path.exists(trace):
                trace = glob.glob(path + "*.trace")[0]
            got = collections.Counter(json.loads(line)["region"] for line in open(trace))
            want = expected(frames, steps, batch, probe)
            diffs = [(r, want[r], got.get(r, 0)) for r in want if got.get(r, 0) != want[r]]
            extra = [r for r in got if r not in want and not r.startswith("_perfmark")]
            label = "frames=%d steps=%d hw=%s" % (frames, steps, state.get("hw", "-"))
            if diffs or extra or meta["unmatched_ends"]:
                bad += 1
                print("MISMATCH %s (%s)" % (label, fname))
                for r, w, g in diffs:
                    print("    %-22s want %-5d got %d" % (r, w, g))
                for r in extra:
                    print("    %-22s unexpected region (%d triggers)" % (r, got[r]))
                if meta["unmatched_ends"]:
                    print("    unmatched_ends = %d" % meta["unmatched_ends"])
            else:
                print("ok       %s: %d regions, %d triggers" %
                      (label, len(want), sum(got[r] for r in want)))
    print("\n%d run(s) checked, %d mismatched" % (len(index["runs"]), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
