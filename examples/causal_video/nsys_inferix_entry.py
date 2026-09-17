"""NVTX boundary around Inferix's second, measured streaming generation.

Used only under Nsight Systems. The first public generation is the full warmup;
the second is the measured call from inferix_runner.py. No runner edit is needed.
"""

import json
from pathlib import Path
import sys

from compat import install as install_compat

install_compat()

import torch
from inferix.pipeline.self_forcing.pipeline import SelfForcingPipeline


_original = SelfForcingPipeline.run_streaming_generation
_calls = 0


def _captured_generation(self, *args, **kwargs):
    global _calls
    _calls += 1
    if _calls == 1:
        return _original(self, *args, **kwargs)
    if _calls != 2:
        raise RuntimeError(f"Expected one warmup and one measured generation, got call {_calls}")

    torch.cuda.nvtx.range_push("causal_generation")
    assert torch.cuda.cudart().cudaProfilerStart() == 0
    try:
        result = _original(self, *args, **kwargs)
        torch.cuda.synchronize()
        return result
    finally:
        assert torch.cuda.cudart().cudaProfilerStop() == 0
        torch.cuda.nvtx.range_pop()


SelfForcingPipeline.run_streaming_generation = _captured_generation


def main():
    if "--output" not in sys.argv:
        raise ValueError("Inferix runner --output is required")
    output = Path(sys.argv[sys.argv.index("--output") + 1])
    if "--warmup-frames" not in sys.argv or int(sys.argv[sys.argv.index("--warmup-frames") + 1]) <= 0:
        raise ValueError("Nsight capture requires a full warmup")
    if "--repetitions" not in sys.argv or sys.argv[sys.argv.index("--repetitions") + 1] != "1":
        raise ValueError("Nsight capture requires one measured repetition")

    import inferix_runner

    inferix_runner.main()
    if _calls != 2:
        raise RuntimeError(f"Expected exactly two Inferix generation calls, got {_calls}")
    (output / "nsys-boundary.json").write_text(json.dumps({
        "nvtx_range": "causal_generation", "capture_range": "cudaProfilerApi", "warmup_calls": 1,
        "measured_calls": 1, "calls": _calls,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
