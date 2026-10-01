#!/usr/bin/env python3
"""Prepare, measure, and report the blinded WAN PCV evaluation suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import core
import wan
import wan_report
import wan_workloads


class WanSuiteError(RuntimeError):
    pass


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _runtime_revision(runtime: Path, expected: str | None = None) -> str:
    runtime = runtime.resolve()
    if not (runtime / "src" / "diffusers" / "__init__.py").is_file():
        raise WanSuiteError(f"not a complete Diffusers source tree: {runtime}")
    result = subprocess.run(
        ["git", "-C", str(runtime), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise WanSuiteError(f"cannot identify Diffusers revision: {result.stderr.strip()}")
    revision = result.stdout.strip()
    if expected is not None and revision != expected:
        raise WanSuiteError(
            f"Diffusers revision mismatch: expected {expected}, found {revision}"
        )
    return revision


def _copy_runtime(template: Path, destination: Path, staged: Path, source_path: str) -> None:
    if destination.exists():
        raise WanSuiteError(f"runtime destination already exists: {destination}")
    shutil.copytree(
        template,
        destination,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )
    source = staged / source_path
    target = destination / source_path
    if not source.is_file() or not target.is_file():
        raise WanSuiteError("staged or runtime target source is missing")
    shutil.copy2(source, target)


def _native_validate(case_id: str, staged: Path, runtime_template: Path, python: str) -> dict[str, Any]:
    manifest = core.read_json(staged / "case.json")
    source_path = manifest["source"]["path"]
    with tempfile.TemporaryDirectory(prefix=f"drperf-{case_id}-native-") as temporary:
        runtime = Path(temporary) / "runtime"
        _copy_runtime(runtime_template, runtime, staged, source_path)
        command = [python, "tests/test_case.py", "--source-root", str(runtime)]
        result = subprocess.run(command, cwd=staged, capture_output=True, text=True, timeout=180)
    marker_hits = None
    for line in reversed(result.stdout.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("marker_hits"), dict):
            marker_hits = payload["marker_hits"].get(case_id)
            break
    if result.returncode or not isinstance(marker_hits, int) or marker_hits < 6:
        raise WanSuiteError(
            f"native workload validation failed for {case_id}: "
            f"returncode={result.returncode}, marker_hits={marker_hits}, "
            f"stderr={result.stderr[-1000:]!r}"
        )
    return {
        "command": command,
        "returncode": result.returncode,
        "marker_hits": marker_hits,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def _replace_clean_export(run_dir: Path, staged: Path, workload_audit: dict[str, Any]) -> dict[str, Any]:
    state = core.load_state(run_dir)
    workspace = run_dir / "selector" / "workspace"
    baseline = run_dir / "controller" / "baseline"
    shutil.rmtree(workspace)
    shutil.rmtree(baseline)
    shutil.copytree(staged, workspace)
    core.write_json(workspace / core.CANDIDATE_FILE, core.candidate_template(1))
    shutil.copytree(workspace, baseline)
    manifest = core.read_json(workspace / "case.json")
    state["source_path"] = manifest["source"]["path"]
    state["baseline_hashes"] = core.hashes(baseline)
    state["command_template"] = manifest["tests"]["command"]
    state["staging"] = "sanitized-read-only-bench_anontated/wan"
    state["workload_minimum_configurations"] = workload_audit["minimum_configurations"]
    core.save_state(run_dir, state)
    (run_dir / "selector" / "PROMPT.md").write_text(core.render_selector_prompt(state))
    return state


def prepare_case(
    case_id: str,
    suite_root: Path,
    runtime_template: Path,
    python: str,
    *,
    threshold: float = 10.0,
    max_iterations: int | None = None,
) -> dict[str, Any]:
    suite_root = suite_root.resolve()
    suite_root.parent.mkdir(parents=True, exist_ok=True)
    run_dir = suite_root / case_id
    if run_dir.exists():
        raise WanSuiteError(f"WAN evaluation already exists: {run_dir}")
    with tempfile.TemporaryDirectory(prefix=f".{case_id}-prepare-", dir=suite_root.parent) as temporary:
        staged = Path(temporary) / "staged"
        staging_audit = wan.stage_wan_case(case_id, staged)
        expected_revision = core.read_json(staged / "case.json").get("source", {}).get("revision")
        if not isinstance(expected_revision, str) or not expected_revision:
            raise WanSuiteError(f"{case_id} has no pinned source revision")
        revision = _runtime_revision(runtime_template, expected_revision)
        workload_audit = wan_workloads.expand_staged_wan_workload(staged)
        native = _native_validate(case_id, staged, runtime_template.resolve(), python)
        core.start(
            case_id,
            run_dir,
            threshold_percent=threshold,
            max_iterations=max_iterations,
            max_pcvs=4,
            python=python,
        )
        state = _replace_clean_export(run_dir, staged, workload_audit)
    state["runtime_template"] = str(runtime_template.resolve())
    state["runtime_revision"] = revision
    core.save_state(run_dir, state)
    _write(run_dir / "controller" / "wan-preparation.json", {
        "case_id": case_id,
        "source": "bench_anontated/wan (read-only, PCVs stripped)",
        "runtime_revision": revision,
        "staging": staging_audit,
        "workload": workload_audit,
        "native_validation": native,
    })
    return {"case_id": case_id, "run_dir": str(run_dir), "marker_hits": native["marker_hits"]}


def prepare_all(
    suite_root: Path,
    runtime_template: Path,
    python: str,
    *,
    threshold: float = 10.0,
    max_iterations: int | None = None,
) -> list[dict[str, Any]]:
    suite_root.mkdir(parents=True, exist_ok=True)
    results = []
    for case_id in wan.list_wan_cases():
        results.append(prepare_case(
            case_id,
            suite_root,
            runtime_template,
            python,
            threshold=threshold,
            max_iterations=max_iterations,
        ))
    return results


def submit_case(suite_root: Path, case_id: str) -> dict[str, Any]:
    return core.submit(suite_root.resolve() / case_id)


def measure_case(suite_root: Path, case_id: str, timeout: float = 180.0):
    run_dir = suite_root.resolve() / case_id
    state = core.load_state(run_dir)
    attempt = state["attempts"][-1]
    attempt_dir = run_dir / attempt["path"]
    runtime = attempt_dir / "runtime"
    if not runtime.exists():
        _copy_runtime(
            Path(state["runtime_template"]),
            runtime,
            attempt_dir / "workspace",
            state["source_path"],
        )
    command = [
        state["substitutions"]["{python}"],
        "tests/test_case.py",
        "--source-root",
        str(runtime),
    ]
    return core.measure(run_dir, timeout=timeout, command_override=command)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("case")
    prepare.add_argument("suite_root", type=Path)
    prepare.add_argument("--runtime-template", type=Path, required=True)
    prepare.add_argument("--python", required=True)
    prepare.add_argument("--threshold", type=float, default=10.0)
    prepare.add_argument("--max-iterations", type=int)
    all_cases = sub.add_parser("prepare-all")
    all_cases.add_argument("suite_root", type=Path)
    all_cases.add_argument("--runtime-template", type=Path, required=True)
    all_cases.add_argument("--python", required=True)
    all_cases.add_argument("--threshold", type=float, default=10.0)
    all_cases.add_argument("--max-iterations", type=int)
    submit = sub.add_parser("submit")
    submit.add_argument("case")
    submit.add_argument("suite_root", type=Path)
    measure = sub.add_parser("measure")
    measure.add_argument("case")
    measure.add_argument("suite_root", type=Path)
    measure.add_argument("--timeout", type=float, default=180.0)
    report = sub.add_parser("report")
    report.add_argument("suite_root", type=Path)

    args = parser.parse_args()
    try:
        if args.action == "prepare":
            value = prepare_case(
                args.case, args.suite_root, args.runtime_template, args.python,
                threshold=args.threshold, max_iterations=args.max_iterations,
            )
        elif args.action == "prepare-all":
            value = prepare_all(
                args.suite_root, args.runtime_template, args.python,
                threshold=args.threshold, max_iterations=args.max_iterations,
            )
        elif args.action == "submit":
            value = submit_case(args.suite_root, args.case)
        elif args.action == "measure":
            feedback, _ = measure_case(args.suite_root, args.case, args.timeout)
            value = feedback
        else:
            value = wan_report.write_reports(args.suite_root, args.suite_root)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except (WanSuiteError, wan.WanStageError, wan_workloads.WanWorkloadError,
            core.EvaluationError, wan_report.ReportError, OSError, ValueError,
            subprocess.SubprocessError) as exc:
        print(f"wan-suite: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

