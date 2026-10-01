#!/usr/bin/env python3
"""Stable scalar-benchmark entry point for the trusted PCV evaluator."""
from pathlib import Path
import sys

EVALUATION = Path(__file__).resolve().parents[1] / "evaluation"
sys.path.insert(0, str(EVALUATION))
from evaluate_pcvs import *  # noqa: F401,F403,E402

if __name__ == "__main__":
    raise SystemExit(main())
