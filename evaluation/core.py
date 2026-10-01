#!/usr/bin/env python3
"""Trusted state and scoring logic for the two-role PCV evaluation."""

from __future__ import annotations

import difflib
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
ANNOTATED_ROOT = REPO_ROOT / "bench_anontated"
COLLECTION_ROOT = REPO_ROOT / "benchmarks" / "regions"
COLLECT = COLLECTION_ROOT / "collect.py"
MEASURE = ANNOTATED_ROOT / "measure.py"
STATE_FILE = "state.json"
CANDIDATE_FILE = "CANDIDATE.json"
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class EvaluationError(RuntimeError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"cannot read JSON from {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_under(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise EvaluationError(f"symlinks are not allowed in an evaluation workspace: {path}")
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc"):
            yield path


def hashes(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): sha256(path) for path in files_under(root)}


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for name, value in hashes(root).items():
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(value.encode())
        digest.update(b"\n")
    return digest.hexdigest()


def annotated_case_ids() -> set[str]:
    result: set[str] = set()
    for manifest in ANNOTATED_ROOT.glob("*/*/case.json"):
        try:
            result.add(str(read_json(manifest)["id"]))
        except (EvaluationError, KeyError, TypeError):
            continue
    return result


def collection_cases() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for manifest in COLLECTION_ROOT.glob("*/cases/*/case.json"):
        data = read_json(manifest)
        case_id = str(data["id"])
        if case_id in result:
            raise EvaluationError(f"duplicate clean benchmark ID: {case_id}")
        result[case_id] = {
            "manifest": manifest,
            "group": manifest.parents[2].name,
            "data": data,
        }
    return result


def available_cases() -> list[dict[str, Any]]:
    annotated = annotated_case_ids()
    clean = collection_cases()
    rows = []
    for case_id in sorted(annotated & set(clean)):
        entry = clean[case_id]
        data = entry["data"]
        rows.append({
            "id": case_id,
            "group": entry["group"],
            "language": data.get("language"),
            "title": data.get("title"),
            "test_status": data.get("tests", {}).get("validation", {}).get("status", "missing"),
        })
    return rows


def load_state(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    state = read_json(run_dir / "controller" / STATE_FILE)
    if state.get("schema_version") != 1:
        raise EvaluationError("unsupported evaluation state schema")
    return state


def save_state(run_dir: Path, state: dict[str, Any]) -> None:
    write_json(run_dir / "controller" / STATE_FILE, state)
    update_summary(run_dir, state)


def candidate_template(iteration: int) -> dict[str, Any]:
    return {
        "iteration": iteration,
        "pcvs": [
            {
                "name": "replace_me",
                "expression": "replace_me_with_an_expression_available_at_region_entry",
                "rationale": "Explain why this state controls instruction count in the marked region.",
            }
        ],
        "hypothesis": "Describe the expected affine instruction-count model.",
    }


def render_selector_prompt(state: dict[str, Any]) -> str:
    feedback = "No Dr. Perf result exists yet."
    if state.get("last_feedback"):
        item = state["last_feedback"]
        if item.get("irregularity_percent") is None:
            feedback = "The previous candidate could not be scored: " + "; ".join(item.get("reasons", []))
        else:
            feedback = (
                f"The previous candidate's irregularity was {item['irregularity_percent']:.6g}%. "
                f"Success requires strictly less than {state['threshold_percent']:.6g}%."
            )
    return f"""# Agent 1: PCV selector

You are iteration {state['next_iteration']} of a blinded performance-critical-variable discovery task for `{state['case_id']}`.

Inspect `workspace/TASK.md`, `workspace/case.json`, the marked source, and the tests. Choose at most {state['max_pcvs']} cheap state expressions available at entry to the marked region that should make its instruction count affine. Expressions may use any cheap mathematical derivation of entry state, such as products, powers, comparisons, conditional expressions, or cardinalities. Coefficients are inferred later; do not provide measured coefficients.

Edit only the target source file named by `workspace/case.json` so its existing marker records your PCVs. Do not change the region boundary, implementation behavior, tests, inputs, or correctness assertions. Fill in `workspace/{CANDIDATE_FILE}` with the same PCV names and expressions.

{feedback}

You must not run, inspect, search for, or invoke Dr. Perf, DynamoRIO, instruction counters, prior benchmark results, `bench_anontated`, controller files, measurement files, or another evaluation attempt. You may run the workload natively for correctness. Your only measurement feedback is `feedback.json` in this directory. Finish after the source annotation and candidate file are ready for submission.
"""


def render_measurer_prompt(run_dir: Path) -> str:
    return f"""# Agent 2: Dr. Perf measurer

This role measures a submitted PCV candidate. It does not propose or edit PCVs and does not communicate Dr. Perf formulas, coefficients, attribution, logs, or source suggestions to Agent 1.

From the Dr. Perf repository, run:

```sh
python3 evaluation/evaluate.py measure {run_dir}
```

The trusted controller validates the run, computes the worst observed-state irregularity, applies the strict threshold, records the iteration, and writes redacted feedback for Agent 1. If dependencies require a custom workload command, place it after `--`.
"""


def start(
    case_id: str,
    run_dir: Path,
    *,
    threshold_percent: float = 10.0,
    max_iterations: int | None = None,
    max_pcvs: int = 4,
    python: str = sys.executable,
    d8: str | None = None,
) -> dict[str, Any]:
    if not 0.0 < threshold_percent <= 100.0:
        raise EvaluationError("threshold must be greater than 0 and at most 100 percent")
    if max_iterations is not None and max_iterations < 1:
        raise EvaluationError("max iterations must be positive")
    if not 1 <= max_pcvs <= 4:
        raise EvaluationError("max PCVs must be between 1 and 4")
    if case_id not in annotated_case_ids():
        raise EvaluationError(f"{case_id!r} is not present in bench_anontated")
    cases = collection_cases()
    if case_id not in cases:
        raise EvaluationError(f"{case_id!r} has no clean empty-marker source export")

    run_dir = run_dir.resolve()
    if run_dir.exists():
        raise EvaluationError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    workspace = run_dir / "selector" / "workspace"
    try:
        subprocess.run(
            [sys.executable, str(COLLECT), "export", case_id, str(workspace)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        shutil.rmtree(run_dir)
        raise

    manifest = read_json(workspace / "case.json")
    source_path = str(manifest["source"]["path"])
    source = workspace / source_path
    if not source.is_file() or not source.resolve().is_relative_to(workspace.resolve()):
        shutil.rmtree(run_dir)
        raise EvaluationError("exported target source is missing or outside the workspace")

    write_json(workspace / CANDIDATE_FILE, candidate_template(1))
    baseline = run_dir / "controller" / "baseline"
    shutil.copytree(workspace, baseline)
    command_template = manifest.get("tests", {}).get("command") or manifest.get("workload", {}).get("command")
    if not isinstance(command_template, list) or not command_template:
        shutil.rmtree(run_dir)
        raise EvaluationError("case has no workload command")

    state = {
        "schema_version": 1,
        "case_id": case_id,
        "group": cases[case_id]["group"],
        "status": "awaiting-selector",
        "threshold_percent": float(threshold_percent),
        "comparison": "strictly-less-than",
        "max_iterations": max_iterations,
        "max_pcvs": max_pcvs,
        "next_iteration": 1,
        "source_path": source_path,
        "baseline_hashes": hashes(baseline),
        "command_template": command_template,
        "substitutions": {"{python}": python, "{d8}": d8},
        "attempts": [],
        "last_feedback": None,
    }
    save_state(run_dir, state)
    (run_dir / "selector" / "PROMPT.md").write_text(render_selector_prompt(state))
    write_json(run_dir / "selector" / "feedback.json", {
        "iteration": 0,
        "status": "not-measured",
        "irregularity_percent": None,
        "threshold_percent": float(threshold_percent),
    })
    (run_dir / "measurement-agent").mkdir()
    (run_dir / "measurement-agent" / "PROMPT.md").write_text(render_measurer_prompt(run_dir))
    return state


def validate_candidate(candidate: Any, iteration: int, max_pcvs: int) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise EvaluationError("candidate must be a JSON object")
    if candidate.get("iteration") != iteration:
        raise EvaluationError(f"candidate iteration must be {iteration}")
    pcvs = candidate.get("pcvs")
    if not isinstance(pcvs, list) or not 1 <= len(pcvs) <= max_pcvs:
        raise EvaluationError(f"candidate must contain between 1 and {max_pcvs} PCVs")
    names: set[str] = set()
    for index, pcv in enumerate(pcvs, 1):
        if not isinstance(pcv, dict):
            raise EvaluationError(f"PCV {index} must be an object")
        name = pcv.get("name")
        expression = pcv.get("expression")
        rationale = pcv.get("rationale")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise EvaluationError(f"PCV {index} has an invalid name")
        if name in names:
            raise EvaluationError(f"duplicate PCV name: {name}")
        names.add(name)
        if not isinstance(expression, str) or not expression.strip() or expression.startswith("replace_me"):
            raise EvaluationError(f"PCV {name} needs a concrete expression")
        if not isinstance(rationale, str) or not rationale.strip():
            raise EvaluationError(f"PCV {name} needs a rationale")
    if not isinstance(candidate.get("hypothesis"), str) or not candidate["hypothesis"].strip():
        raise EvaluationError("candidate needs a nonempty hypothesis")
    return candidate


def validate_workspace(run_dir: Path, state: dict[str, Any]) -> None:
    workspace = run_dir / "selector" / "workspace"
    current = hashes(workspace)
    baseline = state["baseline_hashes"]
    mutable = {state["source_path"], CANDIDATE_FILE}
    for name, digest in baseline.items():
        if name in mutable:
            continue
        if current.get(name) != digest:
            raise EvaluationError(f"selector changed protected benchmark file: {name}")
    added = sorted(set(current) - set(baseline))
    if added:
        raise EvaluationError("selector added unexpected files: " + ", ".join(added))
    if current.get(state["source_path"]) == baseline.get(state["source_path"]):
        raise EvaluationError("target source was not annotated")


def submit(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    state = load_state(run_dir)
    if state["status"] != "awaiting-selector":
        raise EvaluationError(f"cannot submit while status is {state['status']}")
    iteration = state["next_iteration"]
    if state["max_iterations"] is not None and iteration > state["max_iterations"]:
        raise EvaluationError("iteration budget is exhausted")
    workspace = run_dir / "selector" / "workspace"
    candidate = validate_candidate(read_json(workspace / CANDIDATE_FILE), iteration, state["max_pcvs"])
    validate_workspace(run_dir, state)

    attempt_rel = Path("attempts") / f"iteration-{iteration:03d}"
    attempt_dir = run_dir / attempt_rel
    if attempt_dir.exists():
        raise EvaluationError(f"attempt snapshot already exists: {attempt_dir}")
    shutil.copytree(
        workspace,
        attempt_dir / "workspace",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    baseline_source = run_dir / "controller" / "baseline" / state["source_path"]
    candidate_source = workspace / state["source_path"]
    diff = difflib.unified_diff(
        baseline_source.read_text(errors="replace").splitlines(keepends=True),
        candidate_source.read_text(errors="replace").splitlines(keepends=True),
        fromfile="baseline/" + state["source_path"],
        tofile="candidate/" + state["source_path"],
    )
    (attempt_dir / "annotation.diff").write_text("".join(diff))
    attempt = {
        "iteration": iteration,
        "path": attempt_rel.as_posix(),
        "candidate": candidate,
        "workspace_digest": tree_digest(attempt_dir / "workspace"),
        "measurement_runs": [],
        "outcome": "pending",
        "irregularity_percent": None,
    }
    state["attempts"].append(attempt)
    state["status"] = "awaiting-measurement"
    save_state(run_dir, state)
    return attempt


def resolve_command(state: dict[str, Any], workspace: Path, override: list[str] | None) -> list[str]:
    template = override or state["command_template"]
    if not isinstance(template, list) or not template or not all(isinstance(arg, str) for arg in template):
        raise EvaluationError("workload command must be a nonempty argument list")
    substitutions = dict(state["substitutions"])
    substitutions["{source_root}"] = str(workspace)
    command = []
    for arg in template:
        value = substitutions.get(arg, arg)
        if value is None:
            raise EvaluationError(f"workload requires a value for {arg}")
        if "{" in value or "}" in value:
            raise EvaluationError(f"unresolved workload placeholder: {value}")
        command.append(value)
    return command


def assess_metrics(
    metrics: dict[str, Any],
    threshold_percent: float,
    expected_pcvs: list[str] | None = None,
) -> dict[str, Any]:
    reasons = []
    if metrics.get("returncode") != 0:
        reasons.append(f"workload return code {metrics.get('returncode')}")
    if not metrics.get("raw_files"):
        reasons.append("no Dr. Perf measurement files")
    reasons.extend(str(item) for item in metrics.get("validity_warnings", []))
    if not metrics.get("states"):
        reasons.append("target marker has no counted state points")
    if not metrics.get("sufficient_points"):
        reasons.append(
            f"insufficient state points: {metrics.get('distinct_states', 0)}; "
            f"need {metrics.get('required_states', '?')}"
        )
    if metrics.get("dropped_calls"):
        reasons.append(f"{metrics['dropped_calls']} target calls were dropped")
    if metrics.get("nested_calls_per_call"):
        reasons.append("nested marked regions exclude work from target")
    measured_pcvs = metrics.get("pcv_names")
    if expected_pcvs is not None and (
        not isinstance(measured_pcvs, list)
        or len(measured_pcvs) != len(expected_pcvs)
        or set(measured_pcvs) != set(expected_pcvs)
    ):
        reasons.append(
            "measured PCVs do not match the submitted candidate: "
            f"expected {expected_pcvs!r}, measured {measured_pcvs!r}"
        )
    irregularity = metrics.get("max_unexplained_share")
    if (
        not isinstance(irregularity, (int, float))
        or not math.isfinite(irregularity)
        or irregularity < 0.0
    ):
        reasons.append("Dr. Perf did not produce an irregularity value")
        irregularity_percent = None
    else:
        irregularity_percent = float(irregularity) * 100.0
    reasons = list(dict.fromkeys(reasons))
    valid = not reasons
    success = valid and irregularity_percent is not None and irregularity_percent < threshold_percent
    return {
        "valid": valid,
        "success": success,
        "irregularity_percent": irregularity_percent,
        "threshold_percent": threshold_percent,
        "reasons": reasons,
    }


def redacted_feedback(iteration: int, assessment: dict[str, Any], status: str) -> dict[str, Any]:
    feedback = {
        "iteration": iteration,
        "status": status,
        "irregularity_percent": assessment["irregularity_percent"],
        "threshold_percent": assessment["threshold_percent"],
        "comparison": "strictly-less-than",
    }
    if not assessment["valid"] and assessment["irregularity_percent"] is None:
        feedback["reasons"] = assessment["reasons"]
    return feedback


def measure(
    run_dir: Path,
    *,
    timeout: float = 120.0,
    command_override: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    run_dir = run_dir.resolve()
    state = load_state(run_dir)
    if state["status"] != "awaiting-measurement":
        raise EvaluationError(f"cannot measure while status is {state['status']}")
    attempt = state["attempts"][-1]
    attempt_dir = run_dir / attempt["path"]
    workspace = attempt_dir / "workspace"
    if tree_digest(workspace) != attempt["workspace_digest"]:
        raise EvaluationError("submitted attempt changed after it was snapshotted")
    command = resolve_command(state, workspace, command_override)
    run_number = len(attempt["measurement_runs"]) + 1
    while True:
        measurement_rel = Path("measurement") / f"run-{run_number:03d}"
        measurement_dir = attempt_dir / measurement_rel
        if not measurement_dir.exists():
            break
        run_number += 1
    invocation = [
        sys.executable,
        str(MEASURE),
        "run",
        "--case",
        state["case_id"],
        "--workspace",
        str(workspace),
        "--out",
        str(measurement_dir),
        "--timeout",
        str(timeout),
        "--",
        *command,
    ]
    process = subprocess.run(invocation, cwd=REPO_ROOT, capture_output=True, text=True)
    measurement_dir.mkdir(parents=True, exist_ok=True)
    (measurement_dir / "supervisor.stdout.txt").write_text(process.stdout)
    (measurement_dir / "supervisor.stderr.txt").write_text(process.stderr)
    metrics_path = measurement_dir / "metrics.json"
    if metrics_path.is_file():
        metrics = read_json(metrics_path)
    else:
        metrics = {
            "returncode": process.returncode,
            "raw_files": [],
            "states": [],
            "sufficient_points": False,
            "distinct_states": 0,
            "required_states": len(attempt["candidate"]["pcvs"]) + 2,
            "dropped_calls": 0,
            "nested_calls_per_call": 0,
            "max_unexplained_share": None,
            "validity_warnings": ["measurement process did not write metrics.json"],
        }
    expected_pcvs = [pcv["name"] for pcv in attempt["candidate"]["pcvs"]]
    assessment = assess_metrics(metrics, state["threshold_percent"], expected_pcvs)
    measurement_record = {
        "path": measurement_rel.as_posix(),
        "controller_returncode": process.returncode,
        "assessment": assessment,
    }
    attempt["measurement_runs"].append(measurement_record)

    no_output = not metrics.get("raw_files") or not metrics_path.is_file()
    if no_output:
        # Missing measurement artifacts indicate an infrastructure failure and
        # may be retried without charging a new PCV iteration. A nonzero workload
        # return with usable Dr. Perf artifacts is instead a measured invalid
        # candidate (for example, a PCV expression that raises at runtime).
        status = "measurement-error"
        feedback = redacted_feedback(attempt["iteration"], assessment, status)
        attempt["outcome"] = "pending"
        save_state(run_dir, state)
        return feedback, assessment

    if assessment["success"]:
        status = "success"
        state["status"] = "success"
        attempt["outcome"] = "success"
    elif (
        state["max_iterations"] is not None
        and attempt["iteration"] >= state["max_iterations"]
    ):
        status = "exhausted"
        state["status"] = "exhausted"
        attempt["outcome"] = "invalid" if not assessment["valid"] else "exhausted"
    else:
        status = "invalid" if not assessment["valid"] else "retry"
        state["status"] = "awaiting-selector"
        state["next_iteration"] = attempt["iteration"] + 1
        attempt["outcome"] = status
    attempt["irregularity_percent"] = assessment["irregularity_percent"]
    feedback = redacted_feedback(attempt["iteration"], assessment, status)
    state["last_feedback"] = feedback
    write_json(run_dir / "selector" / "feedback.json", feedback)
    if state["status"] == "awaiting-selector":
        write_json(
            run_dir / "selector" / "workspace" / CANDIDATE_FILE,
            candidate_template(state["next_iteration"]),
        )
    (run_dir / "selector" / "PROMPT.md").write_text(render_selector_prompt(state))
    save_state(run_dir, state)
    return feedback, assessment


def update_summary(run_dir: Path, state: dict[str, Any]) -> None:
    attempts = [
        {
            "iteration": item["iteration"],
            "pcvs": [pcv["name"] for pcv in item["candidate"]["pcvs"]],
            "outcome": item["outcome"],
            "irregularity_percent": item["irregularity_percent"],
            "measurement_runs": len(item["measurement_runs"]),
        }
        for item in state["attempts"]
    ]
    successful = next((item["iteration"] for item in attempts if item["outcome"] == "success"), None)
    summary = {
        "schema_version": 1,
        "case_id": state["case_id"],
        "status": state["status"],
        "threshold_percent": state["threshold_percent"],
        "comparison": state["comparison"],
        "iterations_evaluated": sum(item["outcome"] != "pending" for item in attempts),
        "success_iteration": successful,
        "attempts": attempts,
    }
    write_json(run_dir / "summary.json", summary)
