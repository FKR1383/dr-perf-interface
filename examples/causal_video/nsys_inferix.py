"""Prepare a bounded Nsight Systems capture in the managed native A100 container.

Capture starts through the CUDA profiler API at the second Inferix generation,
after a full same-size warmup. An NVTX range labels that measured call. This
is a diagnostic trace; use the uninstrumented native runner for end-to-end
latency.
"""

import argparse
from pathlib import Path
import re
import shlex
import subprocess


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--name", required=True)
parser.add_argument("--tree", default="Inferix-metadata")
parser.add_argument("--kv-residency", choices=("offload", "gpu"), default="offload")
parser.add_argument("--latent-frames", type=int, default=21)
parser.add_argument("--warmup-frames", type=int, default=21)
parser.add_argument("--segments", type=int, default=1)
parser.add_argument("--dry-run", action="store_true", help="Print the managed-container commands without executing")
args = parser.parse_args()
for value in (args.name, args.tree):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", value):
        parser.error("name and tree must contain only letters, digits, hyphens, and underscores")
if args.warmup_frames != args.latent_frames or args.segments != 1:
    parser.error("Use a same-size full warmup and one measured segment for this capture")

root = Path(__file__).resolve().parents[2]
helper = root / "examples/wan_gx/native_container.py"
base = "/workspace/causal"
run = f"{base}/runs/{args.name}"
model_output = f"{run}/model"
nsys = f"{base}/runtime/nsys-2025"
environment = {
    "PYTHONPATH": f"{base}/code:{base}/deps:/workspace/deps:{base}/{args.tree}",
    "LD_LIBRARY_PATH": "/home/jma/bridge-venv2/lib/python3.12/site-packages/nvidia/cudnn/lib",
    "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "PYTHONUNBUFFERED": "1", "PYTHONHASHSEED": "0",
}
command = [
    "env", *(f"{key}={value}" for key, value in environment.items()),
    "timeout", "-k", "20", "1800", nsys, "profile",
    "--trace=cuda,nvtx", "--sample=none", "--cpuctxsw=none",
    "--capture-range=cudaProfilerApi",
    "--capture-range-end=stop", "--export=sqlite",
    f"--output={run}/trace",
    "python3", f"{base}/code/nsys_inferix_entry.py",
    "--role", "native", "--tree", f"{base}/{args.tree}",
    "--base", "/workspace/checkpoint",
    "--checkpoint", f"{base}/models/self-forcing/checkpoints/self_forcing_dmd.pt",
    "--output", model_output, "--latent-frames", str(args.latent_frames),
    "--warmup-frames", str(args.warmup_frames), "--segments", str(args.segments),
    "--repetitions", "1", "--kv-residency", args.kv_residency,
]

script = shlex.join(command) + " > " + shlex.quote(f"{run}/launcher.log") + " 2>&1"
steps = [
    ["python3", str(helper), "command", shlex.join(["mkdir", "-p", run])],
    ["python3", str(helper), "command", script],
]
if args.dry_run:
    for step in steps:
        print(shlex.join(step))
else:
    for step in steps:
        subprocess.run(step, check=True)
