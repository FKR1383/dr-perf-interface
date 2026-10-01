#!/usr/bin/env python3
"""Prepare and measure blinded vLLM PCV benchmark cases."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import core


REPO_ROOT = Path(__file__).resolve().parents[1]
VLLM_ROOT = REPO_ROOT / "bench_anontated" / "vllm"
CASE_RE = re.compile(r"^vllm-[0-9]{3}$")
MIN_MARKER_HITS = 8


class VllmSuiteError(RuntimeError):
    pass


# Compatibility with the shared strict runner's exception tuple.
WanSuiteError = VllmSuiteError


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def list_vllm_cases() -> list[str]:
    cases: list[str] = []
    for path in sorted(VLLM_ROOT.glob("vllm-*/case.json")):
        case_id = path.parent.name
        if CASE_RE.fullmatch(case_id) and core.read_json(path).get("id") == case_id:
            cases.append(case_id)
    return cases


def _runtime_revision(runtime: Path, expected: str | None = None) -> str:
    runtime = runtime.resolve()
    if not (runtime / "vllm" / "__init__.py").is_file():
        raise VllmSuiteError(f"not a complete vLLM source tree: {runtime}")
    result = subprocess.run(
        ["git", "-C", str(runtime), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise VllmSuiteError(f"cannot identify vLLM revision: {result.stderr.strip()}")
    revision = result.stdout.strip()
    if expected is not None and revision != expected:
        raise VllmSuiteError(
            f"vLLM revision mismatch: expected {expected}, found {revision}"
        )
    return revision


def _link_runtime(template: Path, destination: Path, staged: Path, source_path: str) -> None:
    """Create a cheap immutable runtime view and detach its candidate source."""
    if destination.exists():
        raise VllmSuiteError(f"runtime destination already exists: {destination}")
    shutil.copytree(
        template,
        destination,
        copy_function=os.link,
        ignore=shutil.ignore_patterns(
            ".git", ".deps", "build", "__pycache__", "*.pyc", ".pytest_cache"
        ),
    )
    source = staged / source_path
    target = destination / source_path
    if not source.is_file() or not target.is_file():
        raise VllmSuiteError("staged or runtime target source is missing")
    target.unlink()
    shutil.copy2(source, target)


def _environment_command(python: str, staged: Path, runtime: Path) -> list[str]:
    return [
        "/usr/bin/env",
        "PYTHONDONTWRITEBYTECODE=1",
        "VLLM_TARGET_DEVICE=cpu",
        "VLLM_ENABLE_V1_MULTIPROCESSING=0",
        "HF_HUB_OFFLINE=1",
        python,
        "tests/test_case.py",
        "--source-root",
        str(runtime),
    ]


def _native_validate(
    case_id: str, staged: Path, runtime_template: Path, python: str
) -> dict[str, Any]:
    manifest = core.read_json(staged / "case.json")
    source_path = manifest["source"]["path"]
    with tempfile.TemporaryDirectory(prefix=f"drperf-{case_id}-native-") as temporary:
        runtime = Path(temporary) / "runtime"
        _link_runtime(runtime_template, runtime, staged, source_path)
        command = _environment_command(python, staged, runtime)
        result = subprocess.run(
            command,
            cwd=staged,
            capture_output=True,
            text=True,
            timeout=600,
        )
    marker_hits = None
    for line in reversed(result.stdout.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("marker_hits"), dict):
            marker_hits = payload["marker_hits"].get(case_id)
            break
    if result.returncode or not isinstance(marker_hits, int) or marker_hits < MIN_MARKER_HITS:
        raise VllmSuiteError(
            f"native workload validation failed for {case_id}: "
            f"returncode={result.returncode}, marker_hits={marker_hits}, "
            f"required_marker_hits={MIN_MARKER_HITS}, "
            f"stderr={result.stderr[-2000:]!r}"
        )
    return {
        "command": command,
        "returncode": result.returncode,
        "marker_hits": marker_hits,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def prepare_case(
    case_id: str,
    suite_root: Path,
    runtime_template: Path,
    python: str,
    *,
    threshold: float = 10.0,
    max_iterations: int | None = None,
) -> dict[str, Any]:
    if case_id not in list_vllm_cases():
        raise VllmSuiteError(f"unknown vLLM case: {case_id}")
    suite_root = suite_root.resolve()
    suite_root.parent.mkdir(parents=True, exist_ok=True)
    run_dir = suite_root / case_id
    if run_dir.exists():
        raise VllmSuiteError(f"vLLM evaluation already exists: {run_dir}")

    manifest = core.read_json(VLLM_ROOT / case_id / "case.json")
    expected_revision = manifest.get("source", {}).get("revision")
    if not isinstance(expected_revision, str) or not expected_revision:
        raise VllmSuiteError(f"{case_id} has no pinned source revision")
    revision = _runtime_revision(runtime_template, expected_revision)

    with tempfile.TemporaryDirectory(prefix=f".{case_id}-prepare-", dir=suite_root.parent) as temporary:
        staged = Path(temporary) / "staged"
        subprocess.run(
            [sys.executable, str(core.COLLECT), "export", case_id, str(staged)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        native = _native_validate(case_id, staged, runtime_template.resolve(), python)

    core.start(
        case_id,
        run_dir,
        threshold_percent=threshold,
        max_iterations=max_iterations,
        max_pcvs=4,
        python=python,
    )
    state = core.load_state(run_dir)
    state["runtime_template"] = str(runtime_template.resolve())
    state["runtime_revision"] = revision
    state["staging"] = "clean-export-benchmarks/regions"
    core.save_state(run_dir, state)
    _write(
        run_dir / "controller" / "vllm-preparation.json",
        {
            "case_id": case_id,
            "source": "benchmarks/regions clean export",
            "runtime_revision": revision,
            "native_validation": native,
        },
    )
    return {
        "case_id": case_id,
        "run_dir": str(run_dir),
        "marker_hits": native["marker_hits"],
    }


def submit_case(suite_root: Path, case_id: str) -> dict[str, Any]:
    return core.submit(suite_root.resolve() / case_id)


def _consume_marker_expression_error(run_dir: Path):
    """Turn a PCV exception at the marker into an invalid scored attempt."""
    state = core.load_state(run_dir)
    if state["status"] != "awaiting-measurement" or not state["attempts"]:
        return None
    attempt = state["attempts"][-1]
    if not attempt["measurement_runs"]:
        return None
    measurement = attempt["measurement_runs"][-1]
    if measurement.get("controller_returncode") == 0:
        return None
    output = run_dir / attempt["path"] / measurement["path"] / "output.txt"
    if not output.is_file():
        return None
    content = output.read_text(errors="replace")
    case_id = state["case_id"]
    markers = (f'perfmark.region("{case_id}"', f"perfmark.region('{case_id}'")
    if not any(marker in content for marker in markers):
        return None

    assessment = measurement["assessment"]
    reason = "candidate PCV expression raised while evaluating the target marker"
    if reason not in assessment["reasons"]:
        assessment["reasons"].append(reason)
    exhausted = (
        state["max_iterations"] is not None
        and attempt["iteration"] >= state["max_iterations"]
    )
    status = "exhausted" if exhausted else "invalid"
    state["status"] = "exhausted" if exhausted else "awaiting-selector"
    attempt["outcome"] = "invalid"
    attempt["irregularity_percent"] = None
    if not exhausted:
        state["next_iteration"] = attempt["iteration"] + 1
    feedback = core.redacted_feedback(attempt["iteration"], assessment, status)
    state["last_feedback"] = feedback
    core.write_json(run_dir / "selector" / "feedback.json", feedback)
    if not exhausted:
        core.write_json(
            run_dir / "selector" / "workspace" / core.CANDIDATE_FILE,
            core.candidate_template(state["next_iteration"]),
        )
    (run_dir / "selector" / "PROMPT.md").write_text(core.render_selector_prompt(state))
    core.save_state(run_dir, state)
    return feedback, assessment


def measure_case(suite_root: Path, case_id: str, timeout: float = 600.0):
    run_dir = suite_root.resolve() / case_id
    recovered = _consume_marker_expression_error(run_dir)
    if recovered is not None:
        return recovered

    state = core.load_state(run_dir)
    attempt = state["attempts"][-1]
    attempt_dir = run_dir / attempt["path"]
    runtime = attempt_dir / "runtime"
    if runtime.exists():
        shutil.rmtree(runtime)
    _link_runtime(
        Path(state["runtime_template"]),
        runtime,
        attempt_dir / "workspace",
        state["source_path"],
    )
    command = _environment_command(
        state["substitutions"]["{python}"], attempt_dir / "workspace", runtime
    )
    try:
        result = core.measure(run_dir, timeout=timeout, command_override=command)
        if result[0]["status"] == "measurement-error":
            recovered = _consume_marker_expression_error(run_dir)
            if recovered is not None:
                return recovered
        return result
    finally:
        if runtime.exists():
            shutil.rmtree(runtime)

