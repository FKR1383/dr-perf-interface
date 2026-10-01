#!/usr/bin/env python3
"""Stable entry point for isolated scalar-feedback Agent-PCVs runs."""
from pathlib import Path
import sys

EVALUATION = Path(__file__).resolve().parents[1] / "evaluation"
sys.path.insert(0, str(EVALUATION))
from run_agent_pcvs import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(default_feedback="scalar"))
