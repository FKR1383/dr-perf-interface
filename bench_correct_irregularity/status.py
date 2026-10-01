#!/usr/bin/env python3
"""Show scalar-irregularity experiment status without running it."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "evaluation"))
from experiment_status import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(default_root=ROOT / "vllm"))
