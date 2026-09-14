"""Insert perfmark regions into a COPY of the diffusers package (Wan 2.1 T2V path).

    python mark_wan.py /home/ubuntu/drperf-cases/videogen/wan-src/diffusers [--undo]

The copy at videogen/wan-src/diffusers is what run_tiny.py puts first on
sys.path; the editable checkout at videogen/diffusers stays pristine.

(This file would be `mark_diffusers.py`, but another session was concurrently
writing a file of that name into this directory, so it is kept under a name of
its own rather than clobbering theirs.)

Two kinds of mark, both idempotent:

  * METHOD  -- the whole body of `<class>.<method>` is wrapped in
               `with perfmark.region("<name>", <states>):`
  * BLOCK   -- the body of the statement whose stripped text is <anchor>
               (inside `<class>.<method>`) is wrapped the same way.

Declared states are integer keywords, at most four; all of them form the region
key and the cost formula is derived in all of them, so every expression has to
be evaluable at method entry and fit in an int64.  `--undo` restores the .orig
copies.  Style follows /home/ubuntu/drperf/examples/vllm_cpu/mark.py.

No marker sits inside a per-token or per-element loop: the finest of them is
`vae_decode_chunk`, one trigger per latent frame (21 of them at 81 frames).
"""

import os
import re
import shutil
import sys

P = "pipelines/wan/pipeline_wan.py"
T = "models/transformers/transformer_wan.py"
V = "models/autoencoders/autoencoder_kl_wan.py"
S = "schedulers/scheduling_flow_match_euler_discrete.py"

# (file, class, method, region, states)  -- whole method body
METHOD_MARKS = [
    # ---- pipeline: one call, prompt encode, latent allocation
    (P, "WanPipeline", "__call__", "wan_call",
     "num_frames=num_frames, height=height, width=width, steps=num_inference_steps"),
    (P, "WanPipeline", "encode_prompt", "encode_prompt",
     "batch=(len(prompt) if isinstance(prompt, list) else (1 if prompt is not None else prompt_embeds.shape[0]))"),
    (P, "WanPipeline", "prepare_latents", "prepare_latents",
     "num_frames=num_frames, height=height, width=width, batch=batch_size"),

    # ---- transformer: per (step x cfg-branch) call, per layer, per attention
    (T, "WanTransformer3DModel", "forward", "transformer_forward",
     "batch=hidden_states.shape[0], frames=hidden_states.shape[2],"
     " seq_len=(hidden_states.shape[2] // self.config.patch_size[0])"
     " * (hidden_states.shape[3] // self.config.patch_size[1])"
     " * (hidden_states.shape[4] // self.config.patch_size[2])"),
    (T, "WanRotaryPosEmbed", "forward", "rope",
     "frames=hidden_states.shape[2], height=hidden_states.shape[3], width=hidden_states.shape[4]"),
    (T, "WanTimeTextImageEmbedding", "forward", "cond_embed",
     "batch=timestep.shape[0], text_len=encoder_hidden_states.shape[1]"),
    (T, "WanTransformerBlock", "forward", "block",
     "batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], text_len=encoder_hidden_states.shape[1]"),
    # self- and cross-attention share this processor; kv_len separates them
    (T, "WanAttnProcessor", "__call__", "attn",
     "batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], heads=attn.heads,"
     " kv_len=(hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])"),

    # ---- VAE decode: whole decode, the per-latent-frame loop, one decoder pass
    (V, "AutoencoderKLWan", "decode", "vae_decode",
     "batch=z.shape[0], zdim=z.shape[1], frames=z.shape[2], height=z.shape[3]"),
    (V, "AutoencoderKLWan", "_decode", "vae_decode_frames",
     "batch=z.shape[0], frames=z.shape[2], height=z.shape[3]"),
    (V, "AutoencoderKLWan", "clear_cache", "vae_clear_cache",
     "nconv=self._cached_conv_counts['decoder']"),
    (V, "WanDecoder3d", "forward", "vae_decode_chunk",
     "height=x.shape[3], width=x.shape[4], first=int(bool(first_chunk))"),

    # ---- scheduler
    (S, "FlowMatchEulerDiscreteScheduler", "set_timesteps", "set_timesteps",
     "steps=(num_inference_steps or 0)"),
    # NOTE on the state signatures below: drperf's per-thread fast key cache
    # (client/drperf.c get_key) compares the marker's region and state-name
    # strings by POINTER, and with the Python binding those bytes objects are
    # freed and re-allocated at every region.  Two regions that share a root,
    # the same NUMBER of declared states and the same state VALUES can
    # therefore be recorded as one.  It happened here: `sched_step` declared
    # (batch, frames, height, width) = (1, 3, 32, 32) under root `wan_call`,
    # exactly `cfg`'s key, and came out as 8 `cfg` triggers instead of 4, no
    # `sched_step` at all, and 4 "perfmark_end without matching begin".
    # So every region below has a (state count, state values) signature that no
    # other region can take -- `sched_step` uses numel, `vae_decode` carries
    # zdim, `cfg` carries numel, `vae_stage`/`vae_frame_loop` put zdim in a
    # position no other region has.  verify_regions.py re-checks every trigger
    # count against what the code must do, at every grid point.
    (S, "FlowMatchEulerDiscreteScheduler", "step", "sched_step",
     "batch=sample.shape[0], frames=sample.shape[2], numel=sample.numel()"),

    # ---- tensor -> numpy video
    ("video_processor.py", "VideoProcessor", "postprocess_video", "postprocess_video",
     "batch=video.shape[0], frames=video.shape[2], height=video.shape[3], width=video.shape[4]"),
    ("image_processor.py", "VaeImageProcessor", "postprocess", "postprocess_frames",
     "frames=image.shape[0], height=image.shape[2], width=image.shape[3]"),
]

# (file, class, method, anchor line (stripped), region, states)  -- body of a statement
BLOCK_MARKS = [
    (P, "WanPipeline", "__call__", "for i, t in enumerate(timesteps):", "denoise_step",
     "batch=latents.shape[0], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4]"),
    (P, "WanPipeline", "__call__", "if self.do_classifier_free_guidance:", "cfg",
     "frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4], numel=latents.numel()"),
    (P, "WanPipeline", "__call__", 'if not output_type == "latent":', "vae_stage",
     "zdim=latents.shape[1], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4]"),
    (V, "AutoencoderKLWan", "_decode", "for i in range(num_frame):", "vae_frame_loop",
     "frames=num_frame, height=height, width=width, zdim=x.shape[1]"),
]


# --------------------------------------------------------------- source surgery


def _indent(line):
    return len(line) - len(line.lstrip())


_PREFIXED_QUOTE = re.compile(r"^[rRuUbBfF]{0,2}(\"\"\"|''')")


def _docstring_end(lines, k):
    """Index just past a docstring starting at line k, or k if there is none."""
    m = _PREFIXED_QUOTE.match(lines[k].lstrip())
    if not m:
        return k
    q = m.group(1)
    if q in lines[k].lstrip()[m.end():]:          # single-line docstring
        return k + 1
    k += 1
    while q not in lines[k]:
        k += 1
    return k + 1


def _find_method(lines, cls, method):
    """-> (first body line index, indent of the body) for cls.method."""
    in_class = False
    for i, line in enumerate(lines):
        if re.match(r"class %s\b" % re.escape(cls), line):
            in_class = True
            continue
        if re.match(r"class \w", line):
            in_class = False
        if not in_class or not re.match(r"    def %s\(" % re.escape(method), line):
            continue
        # end of the signature: paren depth back to 0 on a line ending in ':'
        j, depth = i, 0
        while True:
            depth += lines[j].count("(") - lines[j].count(")")
            if depth <= 0 and lines[j].rstrip().endswith(":"):
                break
            j += 1
        k = _docstring_end(lines, j + 1)
        while k < len(lines) and not lines[k].strip():
            k += 1
        return k, _indent(lines[k])
    raise SystemExit("mark_wan.py: %s.%s not found" % (cls, method))


def _body_end(lines, start, indent):
    end = start
    while end < len(lines):
        line = lines[end]
        if line.strip() and _indent(line) < indent:
            break
        end += 1
    return end


def _wrap(lines, start, end, indent, region, states):
    head = "%swith perfmark.region(\"%s\", %s):\n" % (" " * indent, region, states)
    body = ["    " + line if line.strip() else line for line in lines[start:end]]
    lines[start:end] = [head] + body


def _ensure_import(src):
    if re.search(r"^import perfmark$", src, re.M):
        return src
    m = re.search(r"^(?:from|import) .*\n", src, re.M)
    pos = m.start() if m else 0
    return src[:pos] + "import perfmark\n" + src[pos:]


def mark_method(src, cls, method, region, states):
    lines = src.splitlines(True)
    start, indent = _find_method(lines, cls, method)
    end = _body_end(lines, start, indent)
    if any('perfmark.region("%s"' % region in line for line in lines[start:end]):
        return src, False
    _wrap(lines, start, end, indent, region, states)
    return _ensure_import("".join(lines)), True


def mark_block(src, cls, method, anchor, region, states):
    lines = src.splitlines(True)
    mstart, _ = _find_method(lines, cls, method)
    mend = _body_end(lines, mstart, _indent(lines[mstart]))
    hits = [i for i in range(mstart, mend) if lines[i].strip() == anchor]
    if len(hits) != 1:
        raise SystemExit("mark_wan.py: anchor %r matched %d times in %s.%s"
                         % (anchor, len(hits), cls, method))
    start = hits[0] + 1
    while start < mend and not lines[start].strip():
        start += 1
    indent = _indent(lines[start])
    end = _body_end(lines, start, indent)
    if any('perfmark.region("%s"' % region in line for line in lines[start:end]):
        return src, False
    _wrap(lines, start, end, indent, region, states)
    return _ensure_import("".join(lines)), True


def main():
    root = os.path.abspath(sys.argv[1])
    undo = "--undo" in sys.argv
    files = sorted({m[0] for m in METHOD_MARKS} | {m[0] for m in BLOCK_MARKS})

    if undo:
        for rel in files:
            full = os.path.join(root, rel)
            if os.path.exists(full + ".orig"):
                shutil.move(full + ".orig", full)
                print("restored", rel)
        return

    for rel in files:
        full = os.path.join(root, rel)
        if not os.path.exists(full + ".orig"):
            shutil.copy(full, full + ".orig")

    for rel, cls, method, region, states in METHOD_MARKS:
        full = os.path.join(root, rel)
        src = open(full).read()
        out, changed = mark_method(src, cls, method, region, states)
        if changed:
            open(full, "w").write(out)
        print("%-9s %s.%s -> %s" % ("marked" if changed else "already", cls, method, region))

    for rel, cls, method, anchor, region, states in BLOCK_MARKS:
        full = os.path.join(root, rel)
        src = open(full).read()
        out, changed = mark_block(src, cls, method, anchor, region, states)
        if changed:
            open(full, "w").write(out)
        print("%-9s %s.%s [%s] -> %s" % ("marked" if changed else "already", cls, method, anchor, region))


if __name__ == "__main__":
    main()
