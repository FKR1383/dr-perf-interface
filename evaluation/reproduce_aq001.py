#!/usr/bin/env python3
"""Compare raw instruction counts for aq-001 with a fixed feature and workload."""
import argparse
from contextlib import contextmanager, redirect_stdout
import csv
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile

try:
    from . import drperf_measure
    from .results import EvaluationError, write_json
except ImportError:
    import drperf_measure
    from results import EvaluationError, write_json

REGION = "aq-001"
FEATURE = "len(enum_class._member_map_)"
COMMAND = ["python3", "tests/test_case.py", "--source-root", "."]
ENV_PREFIX = "DRPERF_DIAGNOSTIC_UNUSED_"


def hashes(workspace):
    return {str(p.relative_to(workspace)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(workspace.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}}


def prepare(source, workspace):
    for name in ("Lib/enum.py", "tests/test_case.py", "tests/marker_probe.py"):
        if not (source / name).is_file():
            raise EvaluationError(f"missing {name}; use a clean aq-001 benchmark export")
    shutil.copytree(source, workspace,
                    ignore=shutil.ignore_patterns(".git", ".codex", ".eval-tmp", "__pycache__", "*.pyc", "*.pyo"))
    target = workspace / "Lib/enum.py"
    original = target.read_text()
    marker = "with perfmark.region('aq-001'):"
    if original.count(marker) != 1:
        raise EvaluationError("expected one uninstrumented aq-001 marker; export a fresh workspace")
    target.write_text(original.replace(
        marker, f"with perfmark.region('{REGION}', **{{'{FEATURE}': {FEATURE}}}):"))


@contextmanager
def extra_environment(count):
    previous = {k: v for k, v in os.environ.items() if k.startswith(ENV_PREFIX)}
    try:
        for key in previous:
            del os.environ[key]
        os.environ.update({f"{ENV_PREFIX}{i}": "padding" for i in range(count)})
        yield
    finally:
        for key in list(os.environ):
            if key.startswith(ENV_PREFIX):
                del os.environ[key]
        os.environ.update(previous)


def compare(runs):
    reference = runs[0]["calls"]
    states = [call["state"] for call in reference]
    if any([call["state"] for call in run["calls"]] != states for run in runs[1:]):
        raise EvaluationError("recorded feature values or their call order differ; cannot compare equal inputs")
    rows = []
    for index, state in enumerate(states):
        row = {"call": index + 1, FEATURE: state[FEATURE]}
        row.update({run["label"]: run["calls"][index]["instructions"] for run in runs})
        rows.append(row)
    return rows


def reproduce(source, output, counts):
    drperf_measure.check_build()
    workspace = output / "workspace"
    prepare(source, workspace)
    frozen = hashes(workspace)
    write_json(output / "setup.json", {
        "region": REGION, "feature": FEATURE, "command": COMMAND,
        "workspace": str(workspace), "source_hashes": frozen, "env_counts": counts,
        "environment_change": f"Add {ENV_PREFIX}0 through {ENV_PREFIX}N-1, each set to 'padding'.",
        "preparation": "Remove workspace bytecode caches before each run; reuse the same workspace and measurement path.",
        "instruction_counts": "Raw per-call self instructions from the trace, before marker calibration; not formula predictions."
    })
    runs = []
    previous = Path.cwd()
    try:
        os.chdir(workspace)
        for index, count in enumerate(counts, 1):
            label = f"run-{index:02d}-env{count}"
            print(f"Measuring {label}...", flush=True)
            for path in list(workspace.rglob("__pycache__")):
                shutil.rmtree(path)
            # The path supplied to the collector stays identical between runs.
            # Completed artifacts are moved aside only after reading the trace.
            current = output / "measurement"
            current.mkdir()
            with extra_environment(count), redirect_stdout(sys.stderr):
                measured = drperf_measure.measure(COMMAND, current, REGION, [FEATURE])
            write_json(current / "measurement.json", measured)
            if measured["status"] != "ok":
                raise EvaluationError(f"{label}: {measured['status']}; see {current}")
            raw = drperf_measure.runner.load_runs(str(current / "raw"))
            traces = [r for r in drperf_measure.runner.load_traces_all(raw) if r["region"] == REGION]
            if not traces or any(set(r["state"]) != {FEATURE} for r in traces):
                raise EvaluationError(f"{label}: missing calls or unexpected recorded feature names")
            calls = [{"state": r["state"], "instructions": r["self"]} for r in traces]
            write_json(current / "calls.json", calls)
            current.rename(output / label)
            if hashes(workspace) != frozen:
                raise EvaluationError(f"{label}: source or workload files changed")
            runs.append({"label": label, "extra_env_vars": count, "calls": calls,
                         "formula": measured["formula"], "irregularity": measured["irregularity"]})
            print(f"  {len(calls)} calls; irregularity {100 * measured['irregularity']:.4f}%", flush=True)
    finally:
        os.chdir(previous)

    rows = compare(runs)
    labels = [run["label"] for run in runs]
    changed = [row for row in rows if len({row[label] for label in labels}) > 1]
    with (output / "counts.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["call", FEATURE, *labels])
        writer.writeheader()
        writer.writerows(rows)
    write_json(output / "comparison.json", {
        "feature": FEATURE, "same_source_and_workload": True, "same_ordered_feature_values": True,
        "call_count": len(rows), "calls_with_different_instruction_counts": len(changed), "runs": runs
    })
    print(f"\nSame source/workload files: yes\nSame feature values and call order: yes ({len(rows)} calls)")
    print(f"Calls with different instruction counts: {len(changed)}/{len(rows)}")
    if changed:
        print("\nRaw instruction counts for the first differing calls (n is the fixed feature):")
        print(f"{'call':>5} {'n':>4}" + "".join(f" {label:>16}" for label in labels))
        for row in changed[:12]:
            print(f"{row['call']:>5} {row[FEATURE]:>4}" + "".join(f" {row[label]:>16}" for label in labels))
    else:
        print("These executions matched. Different instruction counts are possible, not guaranteed.")
    print(f"\nAll calls: {output / 'counts.csv'}\nFormulas and raw artifacts: {output}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True, help="clean aq-001 export; copied before instrumentation")
    parser.add_argument("--results-dir", type=Path, help="new or empty directory; defaults to a retained temporary directory")
    parser.add_argument("--env-counts", type=int, nargs="+", default=[0, 16, 0, 16],
                        help="unused environment variables per run (default: 0 16 0 16); use 0 0 0 0 for unchanged-environment repeats")
    args = parser.parse_args(argv)
    try:
        if len(args.env_counts) < 2 or any(n < 0 or n > 256 for n in args.env_counts):
            raise EvaluationError("supply at least two env-counts, each between 0 and 256")
        source = args.workspace.expanduser().resolve()
        if not source.is_dir():
            raise EvaluationError("workspace must be an existing aq-001 export")
        output = (args.results_dir.expanduser().resolve() if args.results_dir else
                  Path(tempfile.mkdtemp(prefix="drperf-aq001-counts-")))
        if output == source or source in output.parents or output in source.parents:
            raise EvaluationError("source workspace and results directory must be separate")
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            raise EvaluationError("results directory must be empty")
        reproduce(source, output, args.env_counts)
        return 0
    except (EvaluationError, OSError, ValueError) as exc:
        print(f"reproducer: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
