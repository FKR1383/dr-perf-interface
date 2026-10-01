#!/usr/bin/env python3
"""Audit full-feedback isolation without running it."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "evaluation"))
from audit_experiment import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(
        default_root=ROOT / "vllm",
        default_feedback="full",
        default_counterpart=ROOT.parent / "bench_correct_irregularity" / "vllm",
    ))
