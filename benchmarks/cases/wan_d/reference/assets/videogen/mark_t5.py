"""Prompt-encoding markers for the Wan 2.1 text path (`videogen/wan-t5`).

    python mark_t5.py <tree>/diffusers <set> [--fix] [--undo]

`wan-t5` is a copy of `wan-more`, so `_get_t5_prompt_embeds` already carries
mark_more.py's `t5_embeds` / `prompt_clean_r` / `t5_forward` / `t5_repad`.
This script REWRITES that whole method from a template, so it can

  * re-declare the states, in one of two sets:

      sq   t5_embeds / t5_forward / t5_enc  (tag, rtok, ptok, sq)
      sq2  same, with lsq = max_sequence_length**2 // 64 in place of rtok
           rtok = sum of the REAL (unpadded) token lengths
           ptok = batch * max_sequence_length      (the padded token count)
           sq   = batch * max_sequence_length**2 // 64   (quadratic attention)
      lit  t5_embeds / t5_forward / t5_enc  (tag, batch, maxlen, rtok)
           the literal question: does the cost follow `rtok` or `maxlen`?

  * and, with `--fix`, apply the behaviour-preserving fix: run the encoder on
    the LONGEST REAL length rounded up to a multiple of 8 instead of on
    `max_sequence_length`, then zero-pad the sliced outputs to
    `max_sequence_length` exactly as the pipeline already does.

`_pm_rtok` is a HARNESS helper, not part of the pipeline: a declared state has
to be known when the region opens, and the real token lengths are only known
after the tokenizer has run, which is inside the region.  It reproduces the
tokenizer's rule (one token per whitespace-separated piece plus `</s>`, capped
at `max_sequence_length`) from the uncleaned prompt; `prompt_clean` does not
change the piece count for the driver's prompts, which `run_t5.py mode=6`
asserts at the end of every run.

Every region declares `tag=<unique 9xx>` first: drperf's per-thread key cache
compares region and state-name strings by POINTER, so two regions under the
same root with the same state count and the same state values merge.
"""

import os
import re
import shutil
import sys

P = "pipelines/wan/pipeline_wan.py"

HELPER = '''

def _pm_rtok(prompt, max_sequence_length):
    """HARNESS ONLY -- the number of real (unpadded) tokens the tokenizer will
    produce, by the tokenizer's own rule, so it can be declared as a drperf
    state at region open.  Not used by the pipeline."""
    return sum(min(len(u.split()) + 1, max_sequence_length) for u in prompt)

'''

SIG = '''    def _get_t5_prompt_embeds(
        self,
        prompt: str | list[str] = None,
        num_videos_per_prompt: int = 1,
        max_sequence_length: int = 226,
        device: torch.device | None = None,
        dtype: torch.dtype | None = None,
    ):
'''

STATES = {
    "sq": "rtok=_rtok, ptok=_b * max_sequence_length, sq=_b * max_sequence_length * max_sequence_length // 64",
    "lit": "batch=_b, maxlen=max_sequence_length, rtok=_rtok",
    # `sq` answers the question (does the cost follow rtok or the padding?); once
    # it has, rtok is worth less than the state that completes the fit: UMT5 builds
    # the relative-position bias as ONE (1, heads, L, L) tensor per layer and the
    # attention mask as (batch, 1, L, L), so the encoder carries an unbatched L^2
    # term next to the batched one.
    "sq2": "ptok=_b * max_sequence_length, sq=_b * max_sequence_length * max_sequence_length // 64, lsq=max_sequence_length * max_sequence_length // 64",
}

ENC_BASE = '''                prompt_embeds = self.text_encoder(text_input_ids.to(device), mask.to(device)).last_hidden_state
'''

ENC_FIX = '''                # FIX: the encoder does not need the padding.  Run it on the longest
                # REAL length, rounded up to a multiple of 8, with the same mask; the
                # slice-and-zero-pad below already restores the max_sequence_length
                # shape.  T5's scores are shifted by finfo.min at masked positions and
                # its position bias is relative, so every real token's output is
                # independent of how many pad positions follow it.
                n_pad = int(seq_lens.max().item()) if seq_lens.numel() else 0
                # round up to a multiple of 8, with a floor of 16: below M=16 the BLAS
                # picks a different small-matrix kernel and the result changes in the
                # last fp32 ulp (4.2e-06 measured); at 16 and above every trimmed
                # length gives bit-identical output.
                n_pad = min(max(-(-n_pad // 8) * 8, 16), max_sequence_length)
                prompt_embeds = self.text_encoder(
                    text_input_ids[:, :n_pad].to(device), mask[:, :n_pad].to(device)
                ).last_hidden_state
'''

BODY = '''        prompt = [prompt] if isinstance(prompt, str) else prompt
        _b = len(prompt)
        _rtok = _pm_rtok(prompt, max_sequence_length)
        with perfmark.region("t5_embeds", tag=921, %(S)s):
            device = device or self._execution_device
            dtype = dtype or self.text_encoder.dtype

            with perfmark.region("prompt_clean_r", tag=922, batch=_b, chars=sum(len(u) for u in prompt)):
                prompt = [prompt_clean(u) for u in prompt]
            batch_size = len(prompt)

            with perfmark.region("t5_forward", tag=923, %(S)s):
                text_inputs = self.tokenizer(
                    prompt,
                    padding="max_length",
                    max_length=max_sequence_length,
                    truncation=True,
                    add_special_tokens=True,
                    return_attention_mask=True,
                    return_tensors="pt",
                )
                text_input_ids, mask = text_inputs.input_ids, text_inputs.attention_mask
                seq_lens = mask.gt(0).sum(dim=1).long()

                with perfmark.region("t5_enc", tag=926, %(S)s):
%(ENC)s
            with perfmark.region("t5_repad", tag=924, %(S)s):
                prompt_embeds = prompt_embeds.to(dtype=dtype, device=device)
                prompt_embeds = [u[:v] for u, v in zip(prompt_embeds, seq_lens)]
                prompt_embeds = torch.stack(
                    [torch.cat([u, u.new_zeros(max_sequence_length - u.size(0), u.size(1))]) for u in prompt_embeds], dim=0
                )

                # duplicate text embeddings for each generation per prompt, using mps friendly method
                _, seq_len, _ = prompt_embeds.shape
                prompt_embeds = prompt_embeds.repeat(1, num_videos_per_prompt, 1)
                prompt_embeds = prompt_embeds.view(batch_size * num_videos_per_prompt, seq_len, -1)

            return prompt_embeds

'''


def build(setname, fix):
    enc = ENC_FIX if fix else ENC_BASE
    enc = "".join("    " + ln if ln.strip() else ln for ln in enc.splitlines(True))
    return SIG + BODY % {"S": STATES[setname], "ENC": enc}


def main():
    root = os.path.abspath(sys.argv[1])
    args = sys.argv[2:]
    undo = "--undo" in args
    fix = "--fix" in args
    sets = [a for a in args if not a.startswith("--")]
    setname = sets[0] if sets else "sq"
    if setname not in STATES:
        sys.exit("mark_t5.py: unknown set %r (sq|lit)" % setname)

    path = os.path.join(root, P)
    orig = path + ".origT5"
    if not os.path.exists(orig):
        shutil.copy2(path, orig)
    if undo:
        shutil.copy2(orig, path)
        print("mark_t5: restored %s" % path)
        return

    src = open(orig).read()          # always rebuild from the mark_more state
    m = re.search(r"^    def _get_t5_prompt_embeds\(", src, re.M)
    e = re.search(r"^    def encode_prompt\(", src, re.M)
    if not m or not e or e.start() < m.start():
        sys.exit("mark_t5.py: could not locate _get_t5_prompt_embeds")
    new = src[:m.start()] + build(setname, fix) + src[e.start():]
    if "_pm_rtok(prompt" in new and "def _pm_rtok(" not in new:
        im = re.search(r"^import perfmark$", new, re.M)
        pos = new.index("\n", im.end()) + 1
        new = new[:pos] + HELPER + new[pos:]
    open(path, "w").write(new)
    print("mark_t5: %s  set=%s fix=%s" % (path, setname, fix))


if __name__ == "__main__":
    main()
