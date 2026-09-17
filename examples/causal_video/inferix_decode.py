"""Strict opt-in candidate removing Self-Forcing's discarded second VAE decode.

Apply to an isolated Inferix checkout, then compare native original/adapted runs
before using the adaptation in a timing study. No model output is fabricated.
"""

import argparse
import difflib
import hashlib
import json
from pathlib import Path


SOURCE_COMMIT = "77170deca738914c1999bc9e48eea84acb534db3"
RELATIVE = Path("inferix/pipeline/self_forcing/pipeline.py")
SOURCE_SHA256 = "8dbc434f04d0549a340856ce2b4926a368a89185efb85bf5b55a3b823dddbad5"
REFERENCE_ROOT = Path(__file__).resolve().parents[2] / "out/causal-video/Inferix"
OLD = """        # Determine decode_mode based on streaming mode
        # DEFERRED_DECODE: Skip VAE decode in inference, decode externally after offloading generator
        # TRUE_STREAMING: VAE decode happens in block_callback
        decode_mode = DecodeMode.NO_DECODE if resolved_mode == StreamingMode.DEFERRED_DECODE else DecodeMode.AFTER_ALL
"""
NEW = """        # Both streaming paths decode outside inference: in the block callback
        # or after generator offload. The inference result used below is latent.
        decode_mode = DecodeMode.NO_DECODE
"""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def candidate(root):
    path = root / RELATIVE
    before = path.read_bytes()
    if sha256(before) != SOURCE_SHA256:
        raise ValueError(f"source mismatch for {path}: {sha256(before)}; expected {SOURCE_SHA256}")
    source = before.decode()
    if source.count(OLD) != 1:
        raise ValueError("expected exactly one streaming decode-mode selection")
    # Refuse layout drift in the control flow that makes the second decode
    # unused. These guards keep the one-line mode change narrowly justified.
    anchors = {
        "decoded_blocks.append(block_video.cpu())": 2,  # callback and deferred decode
        "block_callback=block_callback,": 1,
        "decode_mode=decode_mode,": 1,
        "if decoded_blocks:\n            full_video = torch.cat(decoded_blocks, dim=1)": 1,
        "self.pipeline.vae.model.clear_cache()": 2,
        "return full_video, final_latents": 1,
    }
    if any(source.count(anchor) != count for anchor, count in anchors.items()):
        raise ValueError("streaming output/callback/cache layout changed; review source")
    # Deferred mode already selects NO_DECODE; only TRUE_STREAMING changes.
    after = source.replace(OLD, NEW).encode()
    return path, before, after


def apply(root):
    if root.resolve() == REFERENCE_ROOT.resolve():
        raise ValueError("refusing to mutate the reference Inferix checkout; copy it first")
    path, before, after = candidate(root)
    path.write_bytes(after)
    manifest = {
        "source_commit": SOURCE_COMMIT,
        "candidate": "skip discarded whole-video decode after true-streaming block decodes",
        "file": str(RELATIVE),
        "source_sha256": sha256(before),
        "adapted_sha256": sha256(after),
        "validation": "candidate only; compare original and adapted native outputs, callbacks, latents and cache state",
    }
    manifest_path = root / "inferix-decode-adaptation.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="isolated Inferix checkout")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="verify source hash and control-flow anchors")
    action.add_argument("--diff", action="store_true", help="print candidate unified diff")
    action.add_argument("--apply", action="store_true", help="apply only to an isolated checkout")
    args = parser.parse_args()
    if args.apply:
        print(apply(args.root))
        return
    path, before, after = candidate(args.root)
    if args.diff:
        print("".join(difflib.unified_diff(
            before.decode().splitlines(keepends=True),
            after.decode().splitlines(keepends=True),
            fromfile=str(path), tofile=str(path) + " (candidate)")), end="")
    else:
        print(f"candidate ready: {path}; source_sha256={sha256(before)}; adapted_sha256={sha256(after)}")


if __name__ == "__main__":
    main()
