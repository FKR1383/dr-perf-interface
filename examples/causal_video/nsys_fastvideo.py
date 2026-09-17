"""Capture FastVideo's measured worker generation after a full native warmup."""

import argparse
from pathlib import Path
import re
import shlex
import subprocess


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--name", required=True)
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()
if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.name):
    parser.error("name must contain only letters, digits, hyphens, and underscores")

root = Path(__file__).resolve().parents[2]
helper = root / "examples/wan_gx/native_container.py"
base = "/workspace/causal"
run = f"{base}/runs/{args.name}"
environment = {
    "PYTHONPATH": f"{base}/code:{base}/FastVideo:{base}/deps:/workspace/deps",
    "LD_LIBRARY_PATH": "/home/jma/bridge-venv2/lib/python3.12/site-packages/nvidia/cudnn/lib",
    "FASTVIDEO_NSYS_CAPTURE": "1", "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "PYTHONUNBUFFERED": "1", "PYTHONHASHSEED": "0",
}
command = [
    "env", *(f"{key}={value}" for key, value in environment.items()),
    "timeout", "-k", "20", "1800", f"{base}/runtime/nsys-2025", "profile",
    "--trace=cuda,nvtx", "--sample=none", "--cpuctxsw=none",
    "--capture-range=cudaProfilerApi", "--capture-range-end=stop",
    f"--output={run}.trace",
    "python3", f"{base}/code/fastvideo_runner.py",
    "--role", "native", "--tree", f"{base}/FastVideo",
    "--model", f"{base}/models/SFWan2.1-T2V-1.3B-Diffusers",
    "--output", run, "--frames", "81", "--height", "480", "--width", "832",
    "--metadata-mode",
]
script = shlex.join(command) + " > " + shlex.quote(f"{run}.log") + " 2>&1"
step = ["python3", str(helper), "command", script]
if args.dry_run:
    print(shlex.join(step))
else:
    subprocess.run(step, check=True)
