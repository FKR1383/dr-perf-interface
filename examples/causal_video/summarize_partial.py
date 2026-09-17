"""Summarize a completed GX partial_sync report without inventing interval costs.

Usage: python3 summarize_partial.py RUN_OR_REPORT --output-prefix PATH
The report may have been generated with --no-trace. A trace enables marked-
interval CPU/GPU work, modeled GPU busy/idle, and largest CPU segments.
"""

import argparse
from bisect import bisect_right
import gzip
import hashlib
import heapq
import json
from pathlib import Path
import re


GPU_EXCLUDED = {"EVENT_RECORD", "EVENT_WAIT", "MALLOC"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ns_ms(value):
    return None if value is None else value / 1e6


def event_stream(path):
    """Read Chrome trace events incrementally, including concatenated gzip members."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        decoder = json.JSONDecoder()
        buffer = ""
        position = 0
        finished = False

        def refill():
            nonlocal buffer, position, finished
            buffer = buffer[position:]
            position = 0
            chunk = stream.read(262144)
            if chunk:
                buffer += chunk
            else:
                finished = True

        while "[" not in buffer:
            refill()
            if finished and "[" not in buffer:
                raise ValueError("traceEvents array missing")
        prefix, buffer = buffer.split("[", 1)
        if not re.fullmatch(r'\s*\{\s*"traceEvents"\s*:\s*', prefix):
            raise ValueError("unexpected trace prefix")
        while True:
            while True:
                while position < len(buffer) and buffer[position] in " \r\n\t,":
                    position += 1
                if position < len(buffer) or finished:
                    break
                refill()
            if position >= len(buffer):
                raise ValueError("truncated traceEvents")
            if buffer[position] == "]":
                return
            try:
                event, end = decoder.raw_decode(buffer, position)
            except json.JSONDecodeError:
                if finished:
                    raise ValueError("invalid or truncated trace event") from None
                refill()
                continue
            position = end
            yield event


def union_ns(spans):
    busy = 0.0
    last_end = float("-inf")
    for start, end in sorted(spans):
        busy += max(0.0, end - max(start, last_end))
        last_end = max(last_end, end)
    return busy


def capture_profile_coverage(run):
    if run is None:
        return []
    rows = []
    for path in sorted(run.glob("host-*/*.log")):
        for line in path.read_text(errors="replace").splitlines():
            if not line.startswith("GXVM_NATIVE_IPC_PROFILE_COVERAGE "):
                continue
            values = dict(re.findall(r"([A-Za-z_]+)=([^ ]+)", line))
            rows.append({"log": str(path), **values})
    return rows


def summarize(input_path, trace_override=None, top=10, run_override=None):
    input_path = input_path.resolve()
    report = (input_path / "timeline-report" if
              (input_path / "timeline-report" / "summary.json").is_file()
              else input_path)
    if not (report / "summary.json").is_file():
        raise ValueError(f"no GX timeline summary in {input_path}")
    run = (run_override.resolve() if run_override else input_path if report != input_path else
           (input_path.parent if (input_path.parent / "result.json").is_file() else None))
    summary_path = report / "summary.json"
    attribution_path = report / "cpu-attribution.json"
    if not attribution_path.is_file():
        raise ValueError(f"missing CPU attribution: {attribution_path}")
    summary = json.loads(summary_path.read_text())
    attribution = json.loads(attribution_path.read_text())
    if summary.get("model") != "optimistic-dependency-timeline":
        raise ValueError("expected GX partial_sync dependency report")
    result_path = run / "result.json" if run else None
    result = json.loads(result_path.read_text()) if result_path and result_path.is_file() else None
    if result is not None and (not result.get("passed") or result.get("cleanup_errors")):
        raise ValueError("run did not pass cleanly; refusing a timing summary")
    trace = trace_override.resolve() if trace_override else next(
        (p for p in (report / "trace.json.gz", report / "trace.json") if p.is_file()), None)
    if trace is not None and not trace.is_file():
        raise ValueError(f"trace does not exist: {trace}")

    rows = []
    indexed = {}
    for item in summary.get("iterations", []):
        start, end = float(item["start_ns"]), float(item["end_ns"])
        if end < start or abs((end - start) - float(item["virtual_ns"])) > max(1e-3, 1e-9 * end):
            raise ValueError("inconsistent iteration interval in GX summary")
        row = {"record": item["record"], "iteration": item["iteration"],
               "start_ns": start, "end_ns": end, "virtual_ns": float(item["virtual_ns"]),
               "cpu_work_ns": None, "gpu_work_ns": None, "gpu_devices": None,
               "largest_cpu_segments_before_gpu_submission": None}
        rows.append(row)
        indexed.setdefault(item["record"], []).append(row)
    if not rows:
        raise ValueError("report has no complete iteration markers")
    for record_rows in indexed.values():
        record_rows.sort(key=lambda x: x["start_ns"])

    if trace:
        lanes = {}
        for row in rows:
            row["cpu_work_ns"] = 0.0
            row["gpu_work_ns"] = 0.0
            row["gpu_devices"] = {}
            row["largest_cpu_segments_before_gpu_submission"] = []
            row["_spans"] = {}
            row["_top"] = []
        serial = 0
        for event in event_stream(trace):
            if event.get("ph") == "M" and event.get("name") == "thread_name":
                lanes[(event.get("pid"), event.get("tid"))] = event.get("args", {}).get("record_lane", "")
                continue
            if event.get("ph") != "X":
                continue
            lane = lanes.get((event.get("pid"), event.get("tid")), "")
            if ":cpu:" in lane:
                record, lane_kind = lane.rsplit(":cpu:", 1)
            elif ":gpu:" in lane:
                record, lane_kind = lane.rsplit(":gpu:", 1)
            else:
                continue
            record_rows = indexed.get(record)
            if not record_rows:
                continue
            kind = event.get("cat")
            is_cpu = ":cpu:" in lane and kind == "cpu"
            is_gpu = ":gpu:" in lane and kind not in GPU_EXCLUDED
            if not (is_cpu or is_gpu):
                continue
            begin = float(event["ts"]) * 1000.0
            end = begin + float(event["dur"]) * 1000.0
            starts = [r["start_ns"] for r in record_rows]
            limit = bisect_right(starts, end)
            for row in record_rows[:limit]:
                device = None
                if is_gpu:
                    device = record + ":gpu:" + lane_kind.split(":stream:", 1)[0]
                    if row["start_ns"] <= begin <= row["end_ns"]:
                        row["_spans"].setdefault(device, [])
                clipped_start = max(begin, row["start_ns"])
                clipped_end = min(end, row["end_ns"])
                amount = clipped_end - clipped_start
                if amount <= 0:
                    continue
                if is_cpu:
                    row["cpu_work_ns"] += amount
                    boundary = event.get("args", {}).get("boundary")
                    if boundary not in ("sync", "mark"):
                        serial += 1
                        segment = {"record_lane": lane, "boundary": boundary,
                                   "start_ns": begin, "duration_ns": float(event["dur"]) * 1000.0,
                                   "within_iteration_ns": amount,
                                   "name": event.get("name"),
                                   "samples": event.get("args", {}).get("samples"),
                                   "estimated_function_breakdown": event.get("args", {}).get("estimated_function_breakdown", [])[:3]}
                        entry = (amount, serial, segment)
                        heap = row["_top"]
                        if len(heap) < top:
                            heapq.heappush(heap, entry)
                        elif entry[:2] > heap[0][:2]:
                            heapq.heapreplace(heap, entry)
                else:
                    row["gpu_work_ns"] += amount
                    row["_spans"].setdefault(device, []).append((clipped_start, clipped_end))
        for row in rows:
            length = row["virtual_ns"]
            row["gpu_devices"] = {
                key: {"busy_ns": busy, "idle_ns": max(0.0, length - busy),
                      "busy_fraction": busy / length if length else None}
                for key, spans in row.pop("_spans").items()
                for busy in [union_ns(spans)]}
            row["largest_cpu_segments_before_gpu_submission"] = [
                entry[2] for entry in sorted(row.pop("_top"), reverse=True)]

    hits = int(summary.get("prediction_hits", 0))
    misses = int(summary.get("prediction_misses", 0))
    errors = int(summary.get("prediction_errors", 0))
    cpu_total = float(attribution.get("cpu_ns", 0))
    sampled_cpu = float(attribution.get("sampled_cpu_ns", 0))
    sources = {"summary": {"path": str(summary_path), "sha256": digest(summary_path)},
               "cpu_attribution": {"path": str(attribution_path), "sha256": digest(attribution_path)},
               "trace": {"path": str(trace), "size_bytes": trace.stat().st_size} if trace else None,
               "result": {"path": str(result_path), "sha256": digest(result_path)} if result else None}
    return {
        "schema": "causal-video-partial-screening-v1", "sources": sources,
        "run_passed": result["passed"] if result else None,
        "model": summary["model"],
        "guaranteed_hardware_lower_bound": bool(summary.get("guaranteed_hardware_lower_bound", False)),
        "interval_evidence_available": trace is not None,
        "capture": {"virtual_ns": summary.get("virtual_ns"),
                    "cpu_work_ns_sum_threads": summary.get("cpu_work_ns"),
                    "gpu_busy_by_device": summary.get("gpu_utilization"),
                    "prediction": {"hits": hits, "misses": misses, "errors": errors,
                                   "disabled": summary.get("prediction_disabled", 0),
                                   "coverage_hits_over_hits_plus_misses": hits/(hits+misses) if hits+misses else None},
                    "cpu_sampling": {"segments": attribution.get("segments"),
                                     "sampled_segments": attribution.get("sampled_segments"),
                                     "sampled_cpu_ns": sampled_cpu,
                                     "unattributed_cpu_ns": attribution.get("unattributed_cpu_ns"),
                                     "sampled_cpu_fraction": sampled_cpu/cpu_total if cpu_total else None,
                                     "samples_used": attribution.get("samples_used"),
                                     "resolved_samples": attribution.get("resolved_samples"),
                                     "unresolved_symbol_samples": attribution.get("unresolved_symbol_samples"),
                                     "low_sample_segments": attribution.get("segments_with_fewer_than_five_samples"),
                                     "native_ipc_profile_coverage_logs": capture_profile_coverage(run)}},
        "iterations": rows,
        "limitations": [
            "Modeled interval CPU work sums overlapping threads; it is not critical-path CPU time.",
            "Modeled GPU idle is not evidence by itself of a CPU bottleneck.",
            "Partial synchronization omits arbitrary CPU mutex, shared-memory and thread-creation dependencies.",
            "Prediction misses and unmodeled copies, memsets and callbacks have zero modeled service cost.",
            "NCCL rendezvous is launch-granular; independent communication contention is omitted.",
            "CPU segment labels name the following interaction, not the exclusive cost of that API.",
            "Prediction and CPU sampling counts are for the whole capture, not individual iterations.",
        ],
    }


def render_md(data):
    c = data["capture"]
    p = c["prediction"]
    sampling = c["cpu_sampling"]
    def fmt(value):
        return "unavailable" if value is None else f"{ns_ms(value):.3f} ms"
    def pct(value):
        return "unavailable" if value is None else f"{100*value:.2f}%"
    lines = ["# GX partial_sync screening evidence", "",
             f"Model: `{data['model']}`. Complete run: `{data['run_passed']}`. "
             f"Marked-interval trace evidence: `{data['interval_evidence_available']}`.", "",
             "| Record | Iteration | Virtual duration | CPU work summed across threads | GPU work summed across streams |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for row in data["iterations"]:
        lines.append(f"| `{row['record']}` | {row['iteration']} | {fmt(row['virtual_ns'])} | {fmt(row['cpu_work_ns'])} | {fmt(row['gpu_work_ns'])} |")
    lines += ["", "Per modeled device within each marked interval (trace-derived):", "",
              "| Record | Iteration | Device | Busy | Idle | Busy fraction |",
              "| --- | ---: | --- | ---: | ---: | ---: |"]
    for row in data["iterations"]:
        for device, values in (row["gpu_devices"] or {}).items():
            lines.append(f"| `{row['record']}` | {row['iteration']} | `{device}` | {fmt(values['busy_ns'])} | {fmt(values['idle_ns'])} | {pct(values['busy_fraction'])} |")
    if not any(row["gpu_devices"] for row in data["iterations"]):
        lines.append("| — | — | unavailable | — | — | — |")
    lines += ["", f"Whole capture: virtual makespan {fmt(c['virtual_ns'])}; "
              f"CPU work summed across threads {fmt(c['cpu_work_ns_sum_threads'])}.",
              f"Compute prediction: {p['hits']} hits, {p['misses']} misses, {p['errors']} errors, "
              f"{p['disabled']} disabled; hit coverage {pct(p['coverage_hits_over_hits_plus_misses'])}.",
              f"CPU attribution: {sampling['sampled_segments']}/{sampling['segments']} sampled segments; "
              f"sampled modeled CPU cost {pct(sampling['sampled_cpu_fraction'])}; "
              f"{sampling['unresolved_symbol_samples']} unresolved-symbol samples; "
              f"{sampling['low_sample_segments']} sampled segments with fewer than five samples.", ""]
    if c["gpu_busy_by_device"]:
        lines += ["Whole-capture modeled GPU device time (denominator: capture makespan):", "",
                  "| Device | Busy | Idle | Busy fraction |",
                  "| --- | ---: | ---: | ---: |"]
        for device, values in c["gpu_busy_by_device"].items():
            lines.append(f"| `{device}` | {fmt(values['busy_ns'])} | {fmt(values['idle_ns'])} | {pct(values['busy_fraction'])} |")
        lines.append("")
    for row in data["iterations"]:
        segments = row["largest_cpu_segments_before_gpu_submission"]
        if segments is None:
            continue
        lines += [f"Largest CPU segments ending at GPU submissions, iteration {row['iteration']} "
                  f"in `{row['record']}`:", "",
                  "| Modeled CPU within interval | Following interaction | Samples | Lane |",
                  "| ---: | --- | ---: | --- |"]
        for seg in segments:
            lines.append(f"| {fmt(seg['within_iteration_ns'])} | `{seg['boundary']}` | {seg['samples']} | `{seg['record_lane']}` |")
        lines.append("")
    lines += ["Interpretation limits:", ""] + [f"- {x}" for x in data["limitations"]]
    lines += ["", "Sources: " + ", ".join(
        f"`{v['path']}`" for v in data["sources"].values() if v), ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="completed run directory or timeline report directory")
    parser.add_argument("--trace", type=Path, help="optional trace from the same capture")
    parser.add_argument("--run-dir", type=Path, help="managed run directory when report was exported elsewhere")
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    if args.top < 1:
        parser.error("--top must be positive")
    data = summarize(args.input, args.trace, args.top, args.run_dir)
    prefix = args.output_prefix.resolve()
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")
    json_path.write_text(json.dumps(data, indent=2) + "\n")
    md_path.write_text(render_md(data))
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
