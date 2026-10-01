#!/usr/bin/env python3
"""Remeasure completed Agent-PCVs guesses without launching an agent.

The historical agent feedback and experiment outcome remain unchanged.  Each
successful replay replaces only the retained Dr. Perf report and workload
output, and records a separate post-hoc assessment in the decision and case
reports.  Progress is checkpointed so an interrupted batch can be resumed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import core
import vllm_suite
import wan_suite


REPO_ROOT = Path(__file__).resolve().parents[1]
MEASURE = REPO_ROOT / "bench_anontated" / "measure.py"


class RemeasureError(RuntimeError):
    pass


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write(path: Path, value: Any) -> None:
    core.write_json(path, value)


def _candidate_digest(candidate: dict[str, Any]) -> str:
    encoded = json.dumps(candidate, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _attempt(state: dict[str, Any], iteration: int) -> dict[str, Any]:
    for attempt in state["attempts"]:
        if attempt["iteration"] == iteration:
            return attempt
    raise RemeasureError(f"controller has no iteration {iteration}")


def remeasure_iteration(
    suite: str,
    suite_root: Path,
    case_id: str,
    iteration_dir: Path,
    timeout: float,
) -> dict[str, Any]:
    run_dir = suite_root / ".controller-runs" / case_id
    state = core.load_state(run_dir)
    iteration = int(iteration_dir.name.rsplit("-", 1)[1])
    attempt = _attempt(state, iteration)
    candidate = _read(iteration_dir / "candidate.json")
    if candidate != attempt["candidate"]:
        raise RemeasureError(f"{case_id} iteration {iteration}: published candidate differs from controller snapshot")

    workspace = run_dir / attempt["path"] / "workspace"
    if core.tree_digest(workspace) != attempt["workspace_digest"]:
        raise RemeasureError(f"{case_id} iteration {iteration}: immutable workspace digest mismatch")
    with tempfile.TemporaryDirectory(prefix=f"drperf-remeasure-{case_id}-{iteration:03d}-") as temporary:
        temporary_root = Path(temporary)
        runtime = temporary_root / "runtime"
        runtime_template = Path(state["runtime_template"])
        if suite == "wan":
            wan_suite._copy_runtime(
                runtime_template, runtime, workspace, state["source_path"]
            )
            command = [
                state["substitutions"]["{python}"],
                "tests/test_case.py",
                "--source-root",
                str(runtime),
            ]
        else:
            vllm_suite._link_runtime(
                runtime_template, runtime, workspace, state["source_path"]
            )
            command = vllm_suite._environment_command(
                state["substitutions"]["{python}"], workspace, runtime
            )
        output = temporary_root / "measurement"
        invocation = [
            sys.executable,
            str(MEASURE),
            "run",
            "--case",
            case_id,
            "--workspace",
            str(workspace),
            "--out",
            str(output),
            "--timeout",
            str(timeout),
            "--",
            *command,
        ]
        process = subprocess.run(
            invocation,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        metrics_path = output / "metrics.json"
        if not metrics_path.is_file():
            raise RemeasureError(
                f"{case_id} iteration {iteration}: measurement wrote no metrics; "
                f"stderr={process.stderr.strip()!r}"
            )
        metrics = _read(metrics_path)
        if not metrics.get("raw_files"):
            raise RemeasureError(
                f"{case_id} iteration {iteration}: measurement produced no Dr. Perf raw files"
            )
        breakdown = metrics.get("irregularity_breakdown")
        if not isinstance(breakdown, dict) or not isinstance(breakdown.get("functions"), list):
            raise RemeasureError(
                f"{case_id} iteration {iteration}: metrics lack function-level irregularity breakdown"
            )

        expected_pcvs = [pcv["name"] for pcv in candidate["pcvs"]]
        assessment = core.assess_metrics(
            metrics, state["threshold_percent"], expected_pcvs
        )
        metrics["posthoc_remeasurement"] = {
            "agent_rerun": False,
            "candidate_sha256": _candidate_digest(candidate),
            "historical_agent_feedback_unchanged": True,
            "purpose": "populate function-level irregularity breakdown",
        }
        _write(iteration_dir / "drperf-full-report.json", metrics)
        workload_output = output / "output.txt"
        if workload_output.is_file():
            shutil.copyfile(workload_output, iteration_dir / "workload-output.txt")

    decision_path = iteration_dir / "script-decision.json"
    decision = _read(decision_path)
    decision["posthoc_remeasurement"] = {
        "assessment": assessment,
        "agent_rerun": False,
        "historical_feedback_unchanged": True,
    }
    _write(decision_path, decision)

    case_report_path = suite_root / case_id / "case-report.json"
    case_report = _read(case_report_path)
    report_attempt = next(
        (item for item in case_report["attempts"] if item["iteration"] == iteration),
        None,
    )
    if report_attempt is None:
        raise RemeasureError(f"{case_id} iteration {iteration}: missing case-report attempt")
    report_attempt["posthoc_remeasurement"] = {
        "assessment": assessment,
        "agent_rerun": False,
        "historical_feedback_unchanged": True,
    }
    _write(case_report_path, case_report)
    return {
        "case": case_id,
        "iteration": iteration,
        "irregularity_percent": assessment["irregularity_percent"],
        "valid": assessment["valid"],
        "functions": len(metrics["irregularity_breakdown"]["functions"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("vllm", "wan"), required=True)
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args()

    suite_root = (
        args.root or REPO_ROOT / "bench_correct_feedback" / args.suite
    ).resolve()
    timeout = args.timeout or (600.0 if args.suite == "vllm" else 240.0)
    checkpoint_path = suite_root / "posthoc-remeasurement-report.json"
    checkpoint = (
        _read(checkpoint_path)
        if checkpoint_path.is_file()
        else {
            "schema_version": 1,
            "suite": args.suite,
            "agent_rerun": False,
            "purpose": "populate function-level irregularity breakdown",
            "measurements": [],
            "errors": [],
        }
    )
    completed = {
        (item["case"], item["iteration"])
        for item in checkpoint.get("measurements", [])
    }
    failures = 0
    for case_id in args.cases:
        expected_prefix = args.suite + "-"
        if not case_id.startswith(expected_prefix):
            parser.error(f"case {case_id!r} does not belong to {args.suite}")
        case_root = suite_root / case_id
        for iteration_dir in sorted((case_root / "iterations").glob("iteration-*")):
            iteration = int(iteration_dir.name.rsplit("-", 1)[1])
            key = (case_id, iteration)
            if key in completed:
                print(json.dumps({"event": "skip", "case": case_id, "iteration": iteration}), flush=True)
                continue
            checkpoint["errors"] = [
                item for item in checkpoint.get("errors", [])
                if (item.get("case"), item.get("iteration")) != key
            ]
            print(json.dumps({"event": "start", "case": case_id, "iteration": iteration}), flush=True)
            try:
                result = remeasure_iteration(
                    args.suite, suite_root, case_id, iteration_dir, timeout
                )
            except Exception as exc:
                failures += 1
                error = {
                    "case": case_id,
                    "iteration": iteration,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                checkpoint["errors"].append(error)
                _write(checkpoint_path, checkpoint)
                print(json.dumps({"event": "error", **error}), flush=True)
                continue
            checkpoint["measurements"].append(result)
            completed.add(key)
            _write(checkpoint_path, checkpoint)
            print(json.dumps({"event": "complete", **result}), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
