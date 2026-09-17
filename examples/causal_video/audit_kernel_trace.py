#!/usr/bin/env python3
"""Audit a measured GX launch trace against a native GPU profile inventory.

This compares observable launch names, grid/block dimensions, API, dynamic
shared memory or cuBLAS hash, prediction hits, and native usable samples.
It does not compare tensor contents or arbitrary kernel arguments.
"""

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

from summarize_partial import event_stream


GX_ONLY_LD_PREFIX = "/opt/gx/nccl-payload/lib:"
GX_DYNAMORIO_LD_PREFIX = re.compile(
    r"(/workspace/\.gx-cache/[0-9a-f]{64}/data/dynamorio/lib64/release:)"
)


def fastvideo_library_identity(native, gx):
    """Normalize only GX's known runtime prefix, with identical loaded cuDNN."""
    left_workers, right_workers = native.get("worker"), gx.get("worker")
    left_dso = (left_workers[0].get("cudnn_dso_sha256") if isinstance(left_workers, list)
                and len(left_workers) == 1 and isinstance(left_workers[0], dict) else None)
    right_dso = (right_workers[0].get("cudnn_dso_sha256") if isinstance(right_workers, list)
                 and len(right_workers) == 1 and isinstance(right_workers[0], dict) else None)
    same_dso = isinstance(left_dso, dict) and bool(left_dso) and left_dso == right_dso
    left_env, right_env = native.get("environment"), gx.get("environment")
    native_ld = left_env.get("LD_LIBRARY_PATH") if isinstance(left_env, dict) else None
    gx_ld = right_env.get("LD_LIBRARY_PATH") if isinstance(right_env, dict) else None
    runtime_prefix = None
    if same_dso and isinstance(native_ld, str) and isinstance(gx_ld, str):
        match = GX_DYNAMORIO_LD_PREFIX.fullmatch(
            gx_ld[len(GX_ONLY_LD_PREFIX):-len(native_ld)]
        ) if native_ld and gx_ld.startswith(GX_ONLY_LD_PREFIX) and gx_ld.endswith(native_ld) else None
        if match:
            runtime_prefix = GX_ONLY_LD_PREFIX + match.group(1)
        elif gx_ld == GX_ONLY_LD_PREFIX + native_ld:
            runtime_prefix = GX_ONLY_LD_PREFIX
    removed = runtime_prefix is not None
    return {"native_ld_library_path": native_ld, "gx_ld_library_path": gx_ld,
            "gx_prefix": runtime_prefix, "gx_prefix_removed": removed,
            "normalized_gx_ld_library_path": native_ld if removed else gx_ld,
            "matching_nonempty_cudnn_dso_hashes": same_dso,
            "native_cudnn_dso_sha256": left_dso, "gx_cudnn_dso_sha256": right_dso}


def framework_of(report):
    if "latent_frames" in report and "streaming_mode" in report:
        return "inferix"
    if "sampling" in report and "worker_start" in report:
        return "fastvideo"
    raise ValueError("unrecognized Inferix/FastVideo report schema")


def measured_interval(report, framework):
    if framework == "inferix":
        start, end = report["start_host_ns"], report["end_host_ns"]
        pid = report["pid"]
        if report.get("clock") != "host_perf_counter_ns":
            raise ValueError("Inferix report does not use host perf_counter_ns")
    else:
        starts, ends = report["worker_start"], report["worker_end"]
        if len(starts) != 1 or len(ends) != 1 or starts[0]["pid"] != ends[0]["pid"]:
            raise ValueError("expected one matching FastVideo worker interval")
        start, end = starts[0]["host_ns"], ends[0]["host_ns"]
        pid = starts[0]["pid"]
    if not isinstance(start, int) or not isinstance(end, int) or end <= start:
        raise ValueError("invalid measured host interval")
    return {"start_host_ns": start, "end_host_ns": end, "pid": pid}


def matched_configuration(native, gx, framework, allowed_source_changes):
    common = ("packages", "prompt")
    specific = (("latent_frames", "segments", "seed", "streaming_mode", "low_memory", "shape",
                 "warmup_frames", "repetitions", "cudnn_version", "cudnn_policy", "harness_sha256",
                 "asset_identity", "kv_residency")
                if framework == "inferix" else ("sampling", "model", "gpu", "metadata_mode",
                                                "repetitions", "resident_dit", "worker_cpu_output",
                                                "cudnn_version",
                                                "cudnn_policy",
                                                "metadata_source_sha256", "stage_verification_enabled"))
    differences = []
    for key in (*common, *specific):
        if key not in native or key not in gx or native[key] != gx[key]:
            differences.append(key)
    if framework == "inferix":
        # Both report host intervals. Their numerical values naturally differ.
        if native.get("clock") != gx.get("clock"):
            differences.append("clock")
    else:
        library_identity = fastvideo_library_identity(native, gx)
        if native.get("result", {}).get("shape") != gx.get("result", {}).get("shape"):
            differences.append("result.shape")
        for key in ("dit_layerwise_offload", "dit_cpu_offload", "worker_cpu_output",
                    "attention_backend",
                    "torch_threads", "torch_interop_threads", "cudnn_version", "cudnn_policy"):
            left_workers, right_workers = native.get("worker"), gx.get("worker")
            if (not isinstance(left_workers, list) or len(left_workers) != 1
                    or not isinstance(right_workers, list) or len(right_workers) != 1
                    or not isinstance(left_workers[0], dict)
                    or not isinstance(right_workers[0], dict)
                    or key not in left_workers[0] or key not in right_workers[0]
                    or left_workers[0][key] != right_workers[0][key]):
                differences.append("worker." + key)
        if not library_identity["matching_nonempty_cudnn_dso_hashes"]:
            differences.append("worker.cudnn_dso_sha256")
        left_env, right_env = native.get("environment"), gx.get("environment")
        for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "PYTHONHASHSEED", "FASTVIDEO_ATTENTION_BACKEND",
                    "TOKENIZERS_PARALLELISM", "FASTVIDEO_WORKER_CPU_OUTPUT"):
            if (not isinstance(left_env, dict) or not isinstance(right_env, dict)
                    or left_env.get(key) != right_env.get(key)):
                differences.append("environment." + key)
        if (library_identity["native_ld_library_path"] !=
                library_identity["normalized_gx_ld_library_path"]):
            differences.append("environment.LD_LIBRARY_PATH")
    left, right = native.get("source_sha256"), gx.get("source_sha256")
    if not isinstance(left, dict) or not isinstance(right, dict) or not left or not right:
        differences.append("source_sha256 missing")
        left, right = left or {}, right or {}
    changes = {key: {"native": left.get(key), "gx": right.get(key)}
               for key in sorted(set(left) | set(right)) if left.get(key) != right.get(key)}
    disallowed = sorted(set(changes) - set(allowed_source_changes))
    if disallowed:
        differences.append("unallowed source changes: " + ", ".join(disallowed))
    return differences, changes


def signature_key(name, grid, block):
    return (name, *(grid[axis] for axis in "xyz"), *(block[axis] for axis in "xyz"))


def canonical_launch_api(api):
    # GX trace names the launch entry point; the native profiler records the
    # corresponding CUDA runtime/driver formal entry point.
    return {"cudaLaunch": "cudaLaunchKernel", "cuLaunch": "cuLaunchKernel",
            "cuLaunchEx": "cuLaunchKernelEx"}.get(api, api)


def database_inventory(path, expected_pid):
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    runs = [dict(row) for row in connection.execute("SELECT * FROM profile_runs")]
    matching = [row for row in runs if row["pid"] == expected_pid]
    if len(matching) != 1 or len(runs) != 1:
        raise ValueError(f"native DB must contain one run for measured PID {expected_pid}; found {[r['pid'] for r in runs]}")
    run_id = matching[0]["id"]
    signatures = [dict(row) for row in connection.execute("SELECT * FROM kernel_signatures")]
    observed = dict(connection.execute(
        "SELECT kernel_id, SUM(count) FROM observed_launches WHERE run_id=? GROUP BY kernel_id", (run_id,)))
    samples = dict(connection.execute(
        "SELECT kernel_id, COUNT(*) FROM kernel_samples WHERE run_id=? AND warmup=0 "
        "AND gate_timed_out=0 AND duration_ns>0 GROUP BY kernel_id", (run_id,)))
    skipped = [dict(row) for row in connection.execute(
        "SELECT * FROM skipped_launches WHERE run_id=?", (run_id,))]
    projected = defaultdict(list)
    counts = Counter()
    by_id = {}
    for row in signatures:
        key = (row["name"], *(row[f"{axis}_{dimension}"] for axis in ("grid", "block")
                              for dimension in "xyz"))
        projected[key].append(row)
        by_id[row["id"]] = row
        if observed.get(row["id"], 0):
            counts[key] += observed[row["id"]]
    unknown_ids = sorted(set(observed) - set(by_id))
    if unknown_ids:
        raise ValueError(f"observed launches lack signatures: {unknown_ids[:10]}")
    connection.close()
    return projected, counts, samples, skipped, matching[0]


def entry(key, value):
    return {"name": key[0], "grid": list(key[1:4]), "block": list(key[4:7]), "count": value}


def entries(counter):
    return [entry(key, value) for key, value in sorted(counter.items())]


def trace_clock(path):
    # gxClock is written after traceEvents by GX. Read only the tail; gzip
    # requires a bounded-memory streaming pass to reach its final member.
    if path.suffix == ".gz":
        tail = ""
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for chunk in iter(lambda: stream.read(262144), ""):
                tail = (tail + chunk)[-4096:]
    else:
        with path.open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 4096))
            tail = stream.read().decode("utf-8", errors="replace")
    match = re.search(r'"gxClock"\s*:\s*"([^"]+)"', tail)
    return match.group(1) if match else None


def audit(native_db, native_report, gx_report, trace, framework="auto", allowed_source_changes=()):
    native = json.loads(native_report.read_text())
    gx = json.loads(gx_report.read_text())
    identified = framework_of(native)
    if framework == "auto":
        framework = identified
    if identified != framework or framework_of(gx) != framework:
        raise ValueError("native and GX reports describe different frameworks")
    if native.get("role") != "gpu-profile" or gx.get("role") not in ("emu", "partial_sync"):
        raise ValueError("expected native gpu-profile and GX emu/partial_sync reports")
    native_interval = measured_interval(native, framework)
    gx_interval = measured_interval(gx, framework)
    differences, source_changes = matched_configuration(native, gx, framework, allowed_source_changes)
    projected, native_counts, samples, skipped, run = database_inventory(native_db, native_interval["pid"])
    emu_counts = Counter()
    missing = Counter()
    ambiguous = Counter()
    metadata_mismatch = Counter()
    no_samples = Counter()
    prediction_misses = Counter()
    malformed = []
    sequences = defaultdict(hashlib.sha256)
    trace_pid = re.search(r"(?:chrome_trace_|pid)(\d+)", trace.name)
    if trace_pid is None:
        differences.append("trace filename lacks GX measured PID")
    elif int(trace_pid.group(1)) != gx_interval["pid"]:
        differences.append("trace filename PID differs from GX measured PID")
    # GX's task timestamps switch to logical time after adoption, but the
    # separate create_ts_us field remains a host enqueue timestamp.
    clock = trace_clock(trace)
    if clock != "host_before_adoption_logical_after_adoption":
        differences.append("GX trace clock does not identify the expected mixed clock")
    start_us, end_us = gx_interval["start_host_ns"] / 1000, gx_interval["end_host_ns"] / 1000
    for event in event_stream(trace):
        if event.get("ph") != "X" or event.get("name") not in ("kernel_predict", "cublas_predict"):
            continue
        args = event.get("args", {})
        create = args.get("create_ts_us")
        if not isinstance(create, (int, float)) or not math.isfinite(create):
            malformed.append("predict event lacks host enqueue timestamp")
            continue
        if not start_us <= create <= end_us:
            continue
        try:
            name = args["kernel_name"] if event["name"] == "kernel_predict" else args["operation"]
            key = signature_key(name, args["grid"], args["block"])
            stream_name = str(args["stream"])
        except (KeyError, TypeError) as error:
            malformed.append(f"measured predict event lacks inventory field: {error}")
            continue
        emu_counts[key] += 1
        metadata = (args.get("shared_mem_bytes") if event["name"] == "kernel_predict"
                    else args.get("param_hash"))
        sequences[stream_name].update(json.dumps((key, metadata), separators=(",", ":")).encode() + b"\n")
        if args.get("prediction_status") != "hit" or args.get("prediction_hit") is not True:
            prediction_misses[key] += 1
        candidates = projected.get(key, [])
        if not candidates:
            missing[key] += 1
            continue
        if len(candidates) != 1:
            ambiguous[key] += 1
            continue
        row = candidates[0]
        if event["name"] == "kernel_predict":
            correct = (canonical_launch_api(args.get("api_type")) == row["api"]
                       and args.get("shared_mem_bytes") == row["dynamic_shared_bytes"])
        else:
            correct = (args.get("operation") == row["api"]
                       and args.get("param_hash") == row["param_hash"] % (1 << 64))
        if not correct:
            metadata_mismatch[key] += 1
        if not samples.get(row["id"]):
            no_samples[key] += 1
    count_differences = {key: {"native": native_counts[key], "gx": emu_counts[key]}
                         for key in native_counts.keys() | emu_counts.keys()
                         if native_counts[key] != emu_counts[key]}
    passed = (not (differences or skipped or malformed or missing or ambiguous or metadata_mismatch
                   or no_samples or prediction_misses or count_differences) and bool(emu_counts))
    return {
        "schema": "causal-video-observable-kernel-audit-v1",
        "framework": framework, "observable_inventory_matches": passed,
        "inputs": {"native_db": str(native_db), "native_report": str(native_report),
                   "gx_report": str(gx_report), "trace": str(trace)},
        "native_profile_run": {"pid": run["pid"], "measurement_mode": run["measurement_mode"]},
        "native_interval": native_interval, "gx_interval": gx_interval,
        "trace_selection": "host create_ts_us within GX measured worker interval; trace task start is not used",
        "trace_clock": clock,
        "config_differences": differences,
        "fastvideo_library_identity": fastvideo_library_identity(native, gx)
        if framework == "fastvideo" else None,
        "source_changes": source_changes,
        "allowed_source_changes": sorted(set(allowed_source_changes)),
        "skipped_native_launches": skipped,
        "native_launches": sum(native_counts.values()), "gx_launches": sum(emu_counts.values()),
        "missing": entries(missing), "ambiguous": entries(ambiguous),
        "mismatched_metadata": entries(metadata_mismatch),
        "without_usable_native_samples": entries(no_samples),
        "prediction_misses_or_errors": entries(prediction_misses),
        "count_differences": [dict(entry(key, value["gx"]), native_count=value["native"])
                              for key, value in sorted(count_differences.items())],
        "malformed_trace_events": malformed[:20],
        "gx_stream_sequence_sha256": {name: digest.hexdigest() for name, digest in sequences.items()},
        "limitations": [
            "Observable launch metadata only; tensor values and arbitrary kernel arguments are not compared.",
            "GX regular-kernel trace omits parameter hashes and cluster dimensions.",
            "Native profile gate and GX measured interval must encompass the same workload; no time scaling is inferred.",
            "Prediction database samples establish modeled latency availability, not numerical correctness.",
            "partial_sync uses host enqueue timestamps for this inventory; its reconstructed virtual timeline is a separate clock.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-db", required=True, type=Path)
    parser.add_argument("--native-report", required=True, type=Path)
    parser.add_argument("--gx-report", required=True, type=Path)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--framework", choices=("auto", "inferix", "fastvideo"), default="auto")
    parser.add_argument("--allow-source-change", action="append", default=[], metavar="RELATIVE_PY_PATH")
    args = parser.parse_args()
    result = audit(args.native_db, args.native_report, args.gx_report, args.trace,
                   args.framework, args.allow_source_change)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"observable kernel audit {'PASS' if result['observable_inventory_matches'] else 'FAIL'}: {args.output}")
    raise SystemExit(0 if result["observable_inventory_matches"] else 2)


if __name__ == "__main__":
    main()
