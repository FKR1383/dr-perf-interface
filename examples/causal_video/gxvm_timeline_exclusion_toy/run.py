#!/usr/bin/env python3
"""CPU-only timeline-client CUDA exclusion regression."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile


def measured(drrun, client, app, cwd):
    p = subprocess.run([str(drrun), "-quiet", "-c", str(client), "--", str(app),
                        "100000"], cwd=cwd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=30, check=True,
                       env=dict(os.environ, GXVM_NATIVE_IPC_REPLAY=""))
    result = re.search(r"CUDA_EXCLUSION_TOY result=(\d+) host=(\d+) stream_events=(\d+)", p.stdout)
    stamps = re.search(r"TIMELINE_STAMPS before=(\d+) after_host=(\d+) inside_before=(\d+) "
                       r"inside_after=(\d+) after_cuda=(\d+) after_tail=(\d+)", p.stdout)
    exclusion = re.search(r"GXVM_TIMELINE_CUDA_EXCLUSION exports=(\d+) calls=(\d+) scopes=(\d+)", p.stdout)
    events = re.search(r"TIMELINE_EVENT_STAMPS stream=(\d+) event=(\d+)", p.stdout)
    if not result or not stamps or not events:
        raise AssertionError(p.stdout)
    return tuple(map(int, result.groups())), tuple(map(int, stamps.groups())), \
        tuple(map(int, exclusion.groups())) if exclusion else None, tuple(map(int, events.groups()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drrun", type=Path, required=True)
    parser.add_argument("--baseline-client", type=Path, required=True)
    parser.add_argument("--patched-client", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="gxvm-timeline-exclusion-") as temp:
        cwd = Path(temp)
        subprocess.run(["gcc", "-O2", "-fPIC", "-shared", "-o", str(cwd / "gx_cuda.so"),
                        str(source / "gx_cuda.c")], check=True)
        subprocess.run(["gcc", "-O2", "-rdynamic", "-o", str(cwd / "app"),
                        str(source / "app.c"), "-ldl"], check=True)
        baseline = measured(args.drrun.resolve(), args.baseline_client.resolve(), cwd / "app", cwd)
        patched = measured(args.drrun.resolve(), args.patched_client.resolve(), cwd / "app", cwd)
    assert baseline[0] == patched[0] == (850000, 300000, 11)
    b, p = baseline[1], patched[1]
    assert b[0] < b[1] < b[2] < b[3] < b[4] < b[5], b
    assert p[0] < p[1] <= p[2] == p[3] <= p[4] < p[5], p
    assert p[1] <= patched[3][0] <= patched[3][1] <= p[2], (p, patched[3])
    assert b[1] <= baseline[3][0] <= baseline[3][1] <= b[2], (b, baseline[3])
    assert p[4] - p[1] < (b[4] - b[1]) // 20, (b, p)
    assert patched[2] == (7, 7, 6), patched
    print(f"PASS result={patched[0]} CUDA_delta_fixed_units={b[4]-b[1]}→{p[4]-p[1]} "
          f"host_head={p[1]-p[0]} host_tail={p[5]-p[4]} nested_scopes=6 "
          f"stream_event_stamps={patched[3]}")


if __name__ == "__main__":
    main()
