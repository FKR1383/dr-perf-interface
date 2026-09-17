"""Opt-in native CPU IPC capture around Inferix's measured generation.

Preload libgxvm_native_ipc_profiler.so and set GXVM_NATIVE_IPC_PROFILE to an
absolute, PID-qualified path before launching this entry in the managed native
container. The frozen inferix_runner.py remains unchanged. No GX emulation or
timing runtime is loaded by this module.
"""

import ctypes
import json
import os
from pathlib import Path
import sys
import time


def argument(name):
    if name not in sys.argv:
        raise ValueError(f"required runner argument missing: {name}")
    position = sys.argv.index(name) + 1
    if position >= len(sys.argv):
        raise ValueError(f"runner argument lacks value: {name}")
    return sys.argv[position]


def check_arguments():
    if argument("--role") != "native":
        raise ValueError("native CPU IPC capture requires --role native")
    if int(argument("--warmup-frames")) <= 0:
        raise ValueError("native CPU IPC capture requires a full warmup")
    if int(argument("--repetitions")) != 1:
        raise ValueError("native CPU IPC capture requires one measured repetition")
    output = Path(argument("--output"))
    pattern = os.environ.get("GXVM_NATIVE_IPC_PROFILE", "")
    if not pattern.startswith("/") or pattern.count("%p") != 1:
        raise ValueError("GXVM_NATIVE_IPC_PROFILE must be absolute with one %p")
    if os.environ.get("GXVM_NATIVE_IPC_AUTOSTART") == "1":
        raise ValueError("autostart would include initialization and warmup")
    if "gx_cuda.so" in Path("/proc/self/maps").read_text():
        raise ValueError("native CPU IPC capture must not preload GX CUDA emulation")
    return output, pattern


OUTPUT, PATTERN = check_arguments()

from compat import install as install_compat
install_compat()

import torch
from inferix.pipeline.self_forcing.pipeline import SelfForcingPipeline

_profile = ctypes.CDLL(None)
_start = _profile.gxvm_ipc_profile_start
_start.argtypes = []
_start.restype = None
_stop = _profile.gxvm_ipc_profile_stop
_stop.argtypes = []
_stop.restype = ctypes.c_int

_original = SelfForcingPipeline.run_streaming_generation
_calls = 0
_interval = None


def _capture(self, *args, **kwargs):
    global _calls, _interval
    _calls += 1
    if _calls == 1:
        return _original(self, *args, **kwargs)
    if _calls != 2:
        raise RuntimeError(f"expected one warmup and one measured generation, got {_calls}")
    started = time.perf_counter_ns()
    _start()
    try:
        result = _original(self, *args, **kwargs)
        torch.cuda.synchronize()
        return result
    finally:
        stopped = time.perf_counter_ns()
        if _stop() != 0:
            raise RuntimeError("native CPU IPC profiler failed to publish profile")
        _interval = {"start_host_ns": started, "end_host_ns": stopped}


SelfForcingPipeline.run_streaming_generation = _capture


def main():
    import inferix_runner
    inferix_runner.main()
    if _calls != 2 or _interval is None:
        raise RuntimeError(f"expected exactly one warmup and one measured generation, got {_calls}")
    profile = Path(PATTERN.replace("%p", str(os.getpid())))
    if not profile.is_file():
        raise RuntimeError(f"native CPU IPC profile not published: {profile}")
    header = profile.open().readline().strip()
    if not header.startswith("GXVM_NATIVE_IPS_V1 "):
        raise RuntimeError("native CPU IPC profile has wrong schema")
    (OUTPUT / "native-cpu-boundary.json").write_text(json.dumps({
        "profile": str(profile), "pid": os.getpid(), "warmup_calls": 1,
        "measured_calls": 1, "host_interval": _interval,
        "instruction_period": os.environ.get("GXVM_NATIVE_IPC_INSTRUCTION_PERIOD"),
        "task_period_ns": os.environ.get("GXVM_NATIVE_IPC_TASK_PERIOD_NS"),
        "profile_header": header,
        "scope": "native GPU generation, after warmup and through CUDA synchronize",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
