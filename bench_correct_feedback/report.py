#!/usr/bin/env python3
"""Write the experiment-level full-feedback report."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "evaluation"))
from aggregate_experiment import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(default_root=ROOT))
