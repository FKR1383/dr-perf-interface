"""Compare saved native FastVideo tensors for metadata-mode semantic validation."""

import argparse
import json
from pathlib import Path

import torch


parser = argparse.ArgumentParser()
parser.add_argument("reference", type=Path)
parser.add_argument("candidate", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

reference = torch.load(args.reference, map_location="cpu", weights_only=True)
candidate = torch.load(args.candidate, map_location="cpu", weights_only=True)
assert reference.shape == candidate.shape
assert reference.dtype == candidate.dtype
delta = (reference.float() - candidate.float()).abs()
report = {
    "reference": str(args.reference),
    "candidate": str(args.candidate),
    "shape": list(reference.shape),
    "dtype": str(reference.dtype),
    "exact_equal": bool(torch.equal(reference, candidate)),
    "different_elements": int(torch.count_nonzero(delta).item()),
    "max_abs": float(delta.max().item()),
    "mean_abs": float(delta.mean().item()),
}
args.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report), flush=True)
