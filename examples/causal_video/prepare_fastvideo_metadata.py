"""Build the pinned FastVideo GX metadata tree with reviewed source adaptations.

The pipeline's actual math, cache writes, and GPU diagnostic operations remain
unchanged. Both native and GX read the diagnostic boolean, then discard it;
neither run chooses a model path from GX's skipped arithmetic result. An opt-in
worker output patch transfers both float and GPU-quantized pixel tensors to CPU
before IPC in both native and GX runs.
"""

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
REVISION = "9b0e57fe4b3a8c112ff24cc22f752eb0608ccfab"
RELATIVE = Path("fastvideo/pipelines/basic/wan/stages/causal_denoising.py")
BASE_SHA256 = "d1d337087f72b16c066f4618eba88443456dd63874fc7b9f0747bfa9d26894f7"
PATCHED_SHA256 = "f4b353c07cb0a94f456caed167d4630fd05b7c3a7a7672eef682fdf531694378"
WORKER_PATCH = Path(__file__).with_name("fastvideo_patches") / "worker_cpu_output.patch"
WORKER_PATCH_SHA256 = "8c82abf5f83043f8bd32d256df7a89f4d8a6d60c4927cec4567effcd40c8d2bc"
WORKER_FILES = {
    Path("fastvideo/worker/multiproc_executor.py"): (
        "f305b9d4d6ebf7bc7ca368af042c873522ee72f93fec67d9ffd3f545d94a51d1",
        "b63199347058a83c3b0d99473d9e7180ecf938aa402e340cc02e4b7a9ed6d809"),
    Path("fastvideo/entrypoints/video_generator.py"): (
        "c49f7691a9c5e66b4f1e75605d1e8fd84f296ad1d419c8359b1d7b5086a70d5f",
        "80eee9501f83ed5898211643b603c09e8dd0cf6c5bef3110836a00edaa30679a"),
}
BEFORE = "        assert torch.isnan(prompt_embeds[0]).sum() == 0\n"
AFTER = ("        # Keep the diagnostic scalar read in both modes but do not branch on\n"
         "        # GX's skipped arithmetic result. The native harness checks finiteness.\n"
         "        bool(torch.isnan(prompt_embeds[0]).sum() == 0)\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "out/causal-video/FastVideo")
    parser.add_argument("--dest", type=Path, default=ROOT / "out/causal-video/FastVideo-metadata")
    args = parser.parse_args()
    source, dest = args.source.resolve(), args.dest.resolve()
    if dest.exists():
        parser.error(f"Destination already exists: {dest}")
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION or sha256(source / RELATIVE) != BASE_SHA256:
        parser.error("FastVideo source revision or causal denoising file differs from pinned input")
    if sha256(WORKER_PATCH) != WORKER_PATCH_SHA256:
        parser.error("Worker output patch differs from reviewed input")
    for relative, (before, _) in WORKER_FILES.items():
        if sha256(source / relative) != before:
            parser.error(f"FastVideo source file differs from pinned input: {relative}")

    shutil.copytree(source, dest, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "assets", "__pycache__", ".pytest_cache"))
    target = dest / RELATIVE
    original = target.read_text()
    if original.count(BEFORE) != 2:
        raise RuntimeError("Expected exactly two causal GPU-value assertions")
    target.write_text(original.replace(BEFORE, AFTER))
    if sha256(target) != PATCHED_SHA256:
        raise RuntimeError("Patched causal source digest differs from reviewed metadata tree")
    subprocess.run(["patch", "-p1", "--fuzz=0", "--batch", "--input", str(WORKER_PATCH)],
                   cwd=dest, check=True)
    for relative, (_, after) in WORKER_FILES.items():
        if sha256(dest / relative) != after:
            raise RuntimeError(f"Patched source digest differs from reviewed metadata tree: {relative}")
    print(dest)


if __name__ == "__main__":
    main()
