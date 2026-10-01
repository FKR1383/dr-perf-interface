#!/usr/bin/env python3
"""Adapters for the non-WAN/non-vLLM annotated benchmark suites."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

import core
import wan


REPO_ROOT = Path(__file__).resolve().parents[1]
ANNOTATED_ROOT = REPO_ROOT / "bench_anontated"
PYTHON_SUITES = {"accidental-quadratic", "growth-multifold"}
V8_SUITES = {"v8-interpreter", "v8-regexp"}
SUPPORTED_SUITES = PYTHON_SUITES | V8_SUITES
GROWTH_CASES = ("aq-003", "vllm-024")


class GenericSuiteError(RuntimeError):
    pass


def list_cases(suite: str) -> list[str]:
    if suite not in SUPPORTED_SUITES:
        raise GenericSuiteError(f"unsupported generic suite: {suite}")
    root = ANNOTATED_ROOT / suite
    if suite == "growth-multifold":
        return [case for case in GROWTH_CASES if (root / case).is_dir()]
    return sorted(
        path.parent.name
        for path in root.glob("*/case.json")
        if core.read_json(path).get("id") == path.parent.name
    )


def unavailable_reason(suite: str) -> str | None:
    if suite in V8_SUITES:
        return (
            "the annotated V8 cases are marked blocked-runtime and this repository "
            "does not contain a pinned, rebuilt, perfmark-linked d8 runtime adapter"
        )
    return None


def _base_manifest(case_id: str) -> dict[str, Any]:
    matches = list(ANNOTATED_ROOT.glob(f"*/{case_id}/case.json"))
    matches = [path for path in matches if path.parent.parent.name != "growth-multifold"]
    if len(matches) != 1:
        raise GenericSuiteError(
            f"cannot identify one base manifest for growth case {case_id}: {matches}"
        )
    return core.read_json(matches[0])


def _stage_growth_case(case_id: str, destination: Path) -> None:
    source_root = ANNOTATED_ROOT / "growth-multifold" / case_id
    if case_id not in list_cases("growth-multifold"):
        raise GenericSuiteError(f"unknown growth-multifold case: {case_id}")
    manifest_path = source_root / "case.json"
    manifest = core.read_json(manifest_path) if manifest_path.is_file() else _base_manifest(case_id)
    source_path = Path(manifest["source"]["path"])
    source = source_root / source_path
    if not source.is_file():
        raise GenericSuiteError(f"growth case source is missing: {source}")

    destination.mkdir(parents=True)
    target = destination / source_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(wan.strip_marker_keywords(source.read_bytes(), case_id))

    tests = source_root / "tests"
    if not tests.is_dir():
        raise GenericSuiteError(f"growth case tests are missing: {tests}")
    shutil.copytree(tests, destination / "tests")
    licenses = source_root / "LICENSES"
    if licenses.is_dir():
        shutil.copytree(licenses, destination / "LICENSES")

    # The specialized growth directories are the authoritative workloads.
    test_files = sorted(
        path.relative_to(destination).as_posix()
        for path in (destination / "tests").rglob("*") if path.is_file()
    )
    manifest = json.loads(json.dumps(manifest))
    manifest["tests"]["files"] = test_files
    manifest["tests"]["command"] = [
        "{python}", "tests/test_case.py", "--source-root", "{source_root}",
    ]
    manifest["workload"]["command"] = manifest["tests"]["command"]
    core.write_json(destination / "case.json", manifest)
    (destination / "TASK.md").write_text(
        f"# Growth-multifold evaluation: {case_id}\n\n"
        "Use the fixed specialized workload in this directory. Select only PCVs "
        "for the existing empty marker; do not change the workload or region.\n"
    )


def _replace_workspace(run_dir: Path, staged: Path, suite: str) -> None:
    state = core.load_state(run_dir)
    workspace = run_dir / "selector" / "workspace"
    baseline = run_dir / "controller" / "baseline"
    shutil.rmtree(workspace)
    shutil.rmtree(baseline)
    shutil.copytree(staged, workspace)
    core.write_json(workspace / core.CANDIDATE_FILE, core.candidate_template(1))
    shutil.copytree(workspace, baseline)
    manifest = core.read_json(workspace / "case.json")
    state["group"] = suite
    state["source_path"] = manifest["source"]["path"]
    state["baseline_hashes"] = core.hashes(baseline)
    state["command_template"] = manifest["tests"]["command"]
    state["staging"] = f"sanitized-read-only-bench_anontated/{suite}"
    core.save_state(run_dir, state)
    (run_dir / "selector" / "PROMPT.md").write_text(core.render_selector_prompt(state))


def prepare_case(
    case_id: str,
    suite: str,
    suite_root: Path,
    python: str,
    *,
    threshold: float = 10.0,
    max_iterations: int | None = None,
) -> dict[str, Any]:
    if suite not in PYTHON_SUITES:
        reason = unavailable_reason(suite)
        raise GenericSuiteError(reason or f"unsupported runnable suite: {suite}")
    if case_id not in list_cases(suite):
        raise GenericSuiteError(f"unknown {suite} case: {case_id}")
    run_dir = suite_root.resolve() / case_id
    if run_dir.exists():
        raise GenericSuiteError(f"evaluation already exists: {run_dir}")

    core.start(
        case_id,
        run_dir,
        threshold_percent=threshold,
        max_iterations=max_iterations,
        max_pcvs=4,
        python=python,
    )
    if suite == "growth-multifold":
        with tempfile.TemporaryDirectory(prefix=f".{case_id}-growth-") as temporary:
            staged = Path(temporary) / "staged"
            _stage_growth_case(case_id, staged)
            _replace_workspace(run_dir, staged, suite)
    state = core.load_state(run_dir)
    state["suite"] = suite
    core.save_state(run_dir, state)
    measurement_agent = run_dir / "measurement-agent"
    if measurement_agent.exists():
        shutil.rmtree(measurement_agent)
    return {"case_id": case_id, "run_dir": str(run_dir)}


def measure_case(run_dir: Path, timeout: float = 120.0):
    return core.measure(run_dir.resolve(), timeout=timeout)


if __name__ == "__main__":
    for suite_name in sorted(SUPPORTED_SUITES):
        print(suite_name, *list_cases(suite_name))
