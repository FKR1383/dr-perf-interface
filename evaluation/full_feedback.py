#!/usr/bin/env python3
"""Full-Dr.-Perf-feedback PCV evaluation with one isolated selector agent."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
from typing import Any

import core
import evaluate_pcvs
import strict_wan
import generic_suite
import vllm_suite
import wan
import wan_suite


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / "bench_correct_feedback"
MAX_ITERATIONS = 10
THRESHOLD_PERCENT = 10.0
INTERNAL_DIR = ".controller-runs"
SCALAR_FEEDBACK_SCHEMA = "score-or-sanitized-invalid-v2"
FULL_FEEDBACK_SCHEMA = "complete-drperf-report-v1"

FULL_AGENT_PROMPT = """# agent_PCVs: full-feedback PCV selector

You are the only PCV-selection agent for exactly one benchmark case. Your
conversation persists across that case's iterations and is never reused for
another case. You have no tools and cannot execute Dr. Perf directly. Treat
Dr. Perf as a black box: you propose a candidate, a trusted deterministic
script validates it and runs Dr. Perf, and on the next turn you receive the
complete Dr. Perf metrics report produced for that candidate.

Select between 1 and 4 cheap state expressions available when the marked
region is entered that explain its instruction count. Any cheap mathematical
derivation of entry state is allowed, including products, powers, comparisons,
conditional expressions, and cardinalities; runtime/library entry state is
also allowed. Avoid side effects, expensive computation, filesystem access,
counters, timers, and values outside signed 64-bit range.

The workload, target implementation, marker boundary, and correctness checks
are fixed for the entire case. Never propose changes to them. Return only the
candidate JSON required by the schema. Success requires valid irregularity
strictly below 10 percent. Coefficients are fitted by Dr. Perf; do not provide
coefficients as separate output.
"""

SCALAR_AGENT_PROMPT = """# agent_PCVs: scalar-feedback PCV selector

You are the only PCV-selection agent for exactly one benchmark case. Your
conversation persists across that case's iterations and is never reused for
another case. You have no tools and cannot execute Dr. Perf directly. Treat
Dr. Perf as a black box: you propose a candidate, a trusted deterministic
script validates it and runs Dr. Perf. After a valid measurement you receive
only the previous candidate's numeric irregularity percentage. If no valid
percentage exists, you receive only a sanitized validity status and reasons;
you never receive formulas, coefficients, per-state values, attribution, or
an irregularity breakdown.

Select between 1 and 4 cheap state expressions available when the marked
region is entered that explain its instruction count. Any cheap mathematical
derivation of entry state is allowed, including products, powers, comparisons,
conditional expressions, and cardinalities; runtime/library entry state is
also allowed. Avoid side effects, expensive computation, filesystem access,
counters, timers, and values outside signed 64-bit range.

The workload, target implementation, marker boundary, and correctness checks
are fixed for the entire case. Never propose changes to them. Return only the
candidate JSON required by the schema. Success requires valid irregularity
strictly below 10 percent. Coefficients are fitted by Dr. Perf; do not provide
coefficients as separate output.
"""

# Backward-compatible name used by existing callers and artifacts.
COMMON_AGENT_PROMPT = FULL_AGENT_PROMPT


def _agent_prompt(feedback_mode: str) -> str:
    if feedback_mode == "full":
        return FULL_AGENT_PROMPT
    if feedback_mode == "scalar":
        return SCALAR_AGENT_PROMPT
    raise FullFeedbackError(f"unsupported feedback mode: {feedback_mode}")


def _protocol(feedback_mode: str) -> str:
    if feedback_mode == "full":
        return "full-drperf-feedback-scripted-measurement"
    if feedback_mode == "scalar":
        return "scalar-irregularity-with-validation-feedback-scripted-measurement"
    raise FullFeedbackError(f"unsupported feedback mode: {feedback_mode}")


class FullFeedbackError(RuntimeError):
    pass


def _feedback_schema(feedback_mode: str) -> str:
    return (
        FULL_FEEDBACK_SCHEMA if feedback_mode == "full"
        else SCALAR_FEEDBACK_SCHEMA
    )


def _ensure_protocol(root: Path, suite: str, feedback_mode: str) -> None:
    """Prevent old numeric-penalty artifacts from being mixed with scalar v2."""
    root.mkdir(parents=True, exist_ok=True)
    expected = {
        "schema_version": 1,
        "suite": suite,
        "feedback_mode": feedback_mode,
        "agent_feedback_schema": _feedback_schema(feedback_mode),
        "agent_model": os.environ.get("DRPERF_AGENT_MODEL", "codex-cli-default"),
    }
    path = root / "experiment-protocol.json"
    if path.is_file():
        if _read(path) != expected:
            raise FullFeedbackError(
                f"experiment protocol mismatch in {path}; use a fresh --root"
            )
        return
    if feedback_mode == "scalar":
        for visible_path in root.glob("*/iterations/*/agent-visible-feedback.json"):
            decision_path = visible_path.with_name("script-decision.json")
            if not decision_path.is_file():
                continue
            visible = _read(visible_path)
            decision = _read(decision_path)
            assessment = decision.get("assessment", {})
            if (
                assessment.get("valid") is False
                and visible == {"irregularity_percent": 100.0}
            ):
                raise FullFeedbackError(
                    f"{root} contains legacy 100%-for-invalid feedback; preserve it "
                    "as an old trial and choose a fresh --root for scalar v2"
                )
    _write(path, expected)


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _digest_rows(rows: list[tuple[str, str]]) -> str:
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def _workload_digest(run_dir: Path) -> str:
    state = core.load_state(run_dir)
    excluded = {state["source_path"], core.CANDIDATE_FILE}
    rows = sorted((name, digest) for name, digest in state["baseline_hashes"].items()
                  if name not in excluded)
    return _digest_rows(rows)


def _agent_state(case_root: Path) -> dict[str, Any]:
    path = case_root / "agent_PCVs" / "state.json"
    if path.is_file():
        return _read(path)
    return {
        "schema_version": 1,
        "thread_id": None,
        "turns": 0,
        "pending_candidate": None,
        "last_report_iteration": None,
    }


def _save_agent_state(case_root: Path, state: dict[str, Any]) -> None:
    _write(case_root / "agent_PCVs" / "state.json", state)


def _scalar_irregularity(report: dict[str, Any]) -> float | None:
    decision = report.get("script_decision", {})
    assessment = decision.get("assessment", {})
    if assessment.get("valid") is not True:
        return None
    value = assessment.get("irregularity_percent")
    return float(value) if isinstance(value, (int, float)) else None


def _scalar_validation_feedback(report: dict[str, Any]) -> dict[str, Any]:
    """Return score-only feedback, or minimal diagnostics when no score exists."""
    decision = report.get("script_decision", {})
    assessment = decision.get("assessment", {})
    value = _scalar_irregularity(report)
    if value is not None:
        return {"irregularity_percent": value}
    reasons = assessment.get("reasons")
    if not isinstance(reasons, list) or not reasons:
        reasons = ["measurement did not produce a valid irregularity percentage"]
    return {
        "status": "invalid",
        "reasons": [str(reason) for reason in reasons],
    }


def _agent_visible_feedback(report: dict[str, Any], feedback_mode: str) -> dict[str, Any]:
    if feedback_mode == "full":
        return report
    if feedback_mode == "scalar":
        return _scalar_validation_feedback(report)
    raise FullFeedbackError(f"unsupported feedback mode: {feedback_mode}")


def _turn_prompt(case_id: str, workspace: Path, iteration: int,
                 report: dict[str, Any] | None,
                 feedback_mode: str = "full") -> str:
    common = _agent_prompt(feedback_mode)
    if report is None:
        material = (
            "\nThis is iteration 1. The complete sanitized benchmark context follows. "
            "No previous annotations or measurements are included.\n\n"
            f"CASE: {case_id}\nSANITIZED BENCHMARK:{strict_wan._file_blocks(workspace)}"
        )
    elif feedback_mode == "scalar":
        visible = _scalar_validation_feedback(report)
        if "irregularity_percent" in visible:
            prefix = f"\nPrevious irregularity: {visible['irregularity_percent']:.12g}%. "
        else:
            prefix = (
                "\nThe previous measurement was invalid. Sanitized validation "
                "feedback follows:\n" + json.dumps(visible, indent=2, sort_keys=True) + "\n"
            )
        material = prefix + (
            f"Return only a replacement candidate JSON for iteration {iteration}. "
            "Use your retained benchmark and attempt context. Success is strictly below 10%."
        )
    else:
        material = (
            f"\nThis is iteration {iteration}. Use your retained benchmark and candidate "
            "history. The trusted script returned the complete Dr. Perf metrics report "
            "for the previous submitted candidate, followed by its deterministic decision.\n\n"
            + json.dumps(report, indent=2, sort_keys=True)
        )
    return common + material


def _rejection_prompt(iteration: int, reason: str,
                      feedback_mode: str = "full") -> str:
    return _agent_prompt(feedback_mode) + (
        f"\nYour proposed candidate for iteration {iteration} was rejected before "
        f"measurement and consumed no iteration. Reason: {reason}\n"
        f"Return a corrected candidate JSON for iteration {iteration}."
    )


def _case_readme(case_id: str, source_path: str,
                 feedback_mode: str = "full") -> str:
    feedback_label = "full-feedback" if feedback_mode == "full" else "scalar-feedback"
    visibility = (
        "the complete Dr. Perf report"
        if feedback_mode == "full"
        else "only a numeric irregularity percentage, or sanitized validity diagnostics when unscorable"
    )
    return f"""# {case_id}: {feedback_label} evaluation

This directory is the human-readable record. Trusted controller state is kept
separately under `../{INTERNAL_DIR}/{case_id}`.

1. `case-actual/` — fixed clean case export; `{source_path}` has an empty marker.
2. `iterations/iteration-NNN/annotation.diff` — only the annotation change.
3. `iterations/iteration-NNN/drperf-full-report.json` — complete Dr. Perf metrics.
4. `case-report.json` and `case-report.md` — complete per-case result.
5. `../full-report.*` — complete benchmark result.
6. `agent_PCVs/PROMPT.md` — common selector instructions used for every benchmark.
7. `agent_PCVs/isolation.json` — isolation and persistent-thread receipt.
8. `iterations/*/script-decision.json` — deterministic black-box controller result.
9. `evaluate_pcvs.sh` — case-local JSON-in/full-Dr.-Perf-report-out command.
10. `iterations/*/agent-visible-feedback.json` — exact feedback exposed to Agent-PCVs.

The workload is immutable across iterations. Exact PCV names and expressions
are recorded in each iteration directory and in the case report. Agent-PCVs
receives {visibility} after each nonterminal measurement.
"""


def _initialize_presentation(case_id: str, root: Path, run_dir: Path,
                             feedback_mode: str = "full", suite: str | None = None) -> Path:
    case_root = root / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    state = core.load_state(run_dir)
    actual = case_root / "case-actual"
    if not actual.exists():
        shutil.copytree(run_dir / "controller" / "baseline", actual)
        candidate = actual / core.CANDIDATE_FILE
        if candidate.exists():
            candidate.unlink()
    agent_dir = case_root / "agent_PCVs"
    agent_dir.mkdir(exist_ok=True)
    (agent_dir / "PROMPT.md").write_text(_agent_prompt(feedback_mode))
    (case_root / "iterations").mkdir(exist_ok=True)
    (case_root / "README.md").write_text(
        _case_readme(case_id, state["source_path"], feedback_mode)
    )
    suite = suite or case_id.split("-", 1)[0]
    evaluator_root = (
        "bench_correct_feedback"
        if feedback_mode == "full"
        else "bench_correct_irregularity"
    )
    evaluator = REPO_ROOT / evaluator_root / "evaluate_pcvs.py"
    launcher = case_root / "evaluate_pcvs.sh"
    launcher.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ $# -ne 1 ]]; then\n"
        '  echo "usage: $0 AGENT_RESPONSE.json" >&2\n'
        "  exit 2\n"
        "fi\n"
        f"exec python3 {shlex.quote(str(evaluator))} "
        f"--suite {shlex.quote(suite)} "
        f"--run-dir {shlex.quote(str(run_dir.resolve()))} "
        '--candidate "$1"\n'
    )
    launcher.chmod(0o755)
    receipt = {
        "case_id": case_id,
        "agent_role": "agent_PCVs",
        "fresh_thread_per_case": True,
        "persistent_only_within_case": True,
        "tools_disabled": list(strict_wan.DISABLED_FEATURES),
        "drperf_access": "indirect through trusted deterministic script only",
        "measurement_agent": None,
        "full_metrics_returned_after_each_iteration": feedback_mode == "full",
        "feedback_mode": feedback_mode,
        "agent_feedback_schema": _feedback_schema(feedback_mode),
        "agent_model": os.environ.get("DRPERF_AGENT_MODEL", "codex-cli-default"),
        "agent_visible_feedback": (
            "complete Dr. Perf metrics report"
            if feedback_mode == "full"
            else "numeric irregularity percentage or sanitized invalid-measurement diagnostics"
        ),
        "fixed_workload_digest": _workload_digest(run_dir),
        "thread_id": _agent_state(case_root)["thread_id"],
    }
    _write(agent_dir / "isolation.json", receipt)
    return case_root


def _prepare_wan_case(case_id: str, root: Path, runtime: Path, python: str,
                      feedback_mode: str = "full") -> tuple[Path, Path]:
    internal_root = root / INTERNAL_DIR
    run_dir = internal_root / case_id
    if not run_dir.exists():
        wan_suite.prepare_case(
            case_id, internal_root, runtime, python,
            threshold=THRESHOLD_PERCENT, max_iterations=MAX_ITERATIONS,
        )
    unused_measurement_agent = run_dir / "measurement-agent"
    if unused_measurement_agent.exists():
        shutil.rmtree(unused_measurement_agent)
    case_root = _initialize_presentation(case_id, root, run_dir, feedback_mode, "wan")
    return run_dir, case_root


def _prepare_vllm_case(case_id: str, root: Path, runtime: Path, python: str,
                       feedback_mode: str = "full") -> tuple[Path, Path]:
    internal_root = root / INTERNAL_DIR
    run_dir = internal_root / case_id
    if not run_dir.exists():
        vllm_suite.prepare_case(
            case_id, internal_root, runtime, python,
            threshold=THRESHOLD_PERCENT, max_iterations=MAX_ITERATIONS,
        )
    unused_measurement_agent = run_dir / "measurement-agent"
    if unused_measurement_agent.exists():
        shutil.rmtree(unused_measurement_agent)
    case_root = _initialize_presentation(case_id, root, run_dir, feedback_mode, "vllm")
    return run_dir, case_root


def _prepare_generic_case(case_id: str, suite: str, root: Path, python: str,
                          feedback_mode: str = "full") -> tuple[Path, Path]:
    internal_root = root / INTERNAL_DIR
    run_dir = internal_root / case_id
    if not run_dir.exists():
        generic_suite.prepare_case(
            case_id, suite, internal_root, python,
            threshold=THRESHOLD_PERCENT, max_iterations=MAX_ITERATIONS,
        )
    measurement_agent = run_dir / "measurement-agent"
    if measurement_agent.exists():
        shutil.rmtree(measurement_agent)
    return run_dir, _initialize_presentation(
        case_id, root, run_dir, feedback_mode, suite
    )


def _measurement_payload(run_dir: Path) -> dict[str, Any]:
    state = core.load_state(run_dir)
    attempt = state["attempts"][-1]
    measurement = attempt["measurement_runs"][-1]
    measurement_dir = run_dir / attempt["path"] / measurement["path"]
    metrics_path = measurement_dir / "metrics.json"
    metrics = _read(metrics_path) if metrics_path.is_file() else None
    return {
        "case_id": state["case_id"],
        "iteration": attempt["iteration"],
        "candidate": attempt["candidate"],
        "drperf_full_report": metrics,
        "script_decision": {
            "assessment": measurement["assessment"],
            "threshold_percent": state["threshold_percent"],
            "comparison": state["comparison"],
            "controller_returncode": measurement["controller_returncode"],
            "status": state["status"],
        },
        "fixed_workload_digest": _workload_digest(run_dir),
    }


def _publish_iteration(run_dir: Path, case_root: Path,
                       feedback: dict[str, Any], assessment: dict[str, Any],
                       feedback_mode: str = "full") -> dict[str, Any]:
    state = core.load_state(run_dir)
    attempt = state["attempts"][-1]
    measurement = attempt["measurement_runs"][-1]
    source = run_dir / attempt["path"]
    measurement_dir = source / measurement["path"]
    destination = case_root / "iterations" / f"iteration-{attempt['iteration']:03d}"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "annotation.diff", destination / "annotation.diff")
    _write(destination / "candidate.json", attempt["candidate"])
    script_decision = {
        "feedback": feedback,
        "assessment": assessment,
        "workload_digest": _workload_digest(run_dir),
    }
    _write(destination / "script-decision.json", script_decision)
    metrics = measurement_dir / "metrics.json"
    if metrics.is_file():
        shutil.copy2(metrics, destination / "drperf-full-report.json")
    output = measurement_dir / "output.txt"
    if output.is_file():
        shutil.copy2(output, destination / "workload-output.txt")
    execution = measurement_dir / "execution.json"
    if execution.is_file():
        shutil.copy2(execution, destination / "execution.json")
    payload = _measurement_payload(run_dir)
    payload["script_decision"] = script_decision
    _write(
        destination / "agent-visible-feedback.json",
        _agent_visible_feedback(payload, feedback_mode),
    )
    runtime = source / "runtime"
    if runtime.exists():
        shutil.rmtree(runtime)
    return payload


def _write_case_report(run_dir: Path, case_root: Path, agent: dict[str, Any],
                       feedback_mode: str = "full") -> dict[str, Any]:
    state = core.load_state(run_dir)
    attempts = []
    for attempt in state["attempts"]:
        assessment = attempt["measurement_runs"][-1]["assessment"] if attempt["measurement_runs"] else None
        attempts.append({
            "iteration": attempt["iteration"],
            "outcome": attempt["outcome"],
            "irregularity_percent": attempt["irregularity_percent"],
            "pcvs": attempt["candidate"]["pcvs"],
            "hypothesis": attempt["candidate"]["hypothesis"],
            "assessment": assessment,
            "annotation_diff": f"iterations/iteration-{attempt['iteration']:03d}/annotation.diff",
            "drperf_full_report": f"iterations/iteration-{attempt['iteration']:03d}/drperf-full-report.json",
        })
    report = {
        "schema_version": 1,
        "case": state["case_id"],
        "status": state["status"],
        "iterations": len(state["attempts"]),
        "threshold_percent": state["threshold_percent"],
        "comparison": state["comparison"],
        "measurement_agent": None,
        "measurement_and_scoring": "trusted deterministic script",
        "feedback_mode": feedback_mode,
        "agent_feedback_schema": _feedback_schema(feedback_mode),
        "agent_model": os.environ.get("DRPERF_AGENT_MODEL", "codex-cli-default"),
        "agent_visible_feedback": (
            "complete Dr. Perf metrics report"
            if feedback_mode == "full"
            else "numeric irregularity percentage or sanitized invalid-measurement diagnostics"
        ),
        "agent_PCVs_thread": agent["thread_id"],
        "fixed_workload_digest": _workload_digest(run_dir),
        "attempts": attempts,
    }
    _write(case_root / "case-report.json", report)
    lines = [
        f"# {state['case_id']} full-feedback result", "",
        f"Status: `{state['status']}`; iterations: {len(attempts)}; "
        f"fixed workload: `{report['fixed_workload_digest']}`.", "",
        "| iteration | exact PCVs | irregularity | outcome |", "| ---: | --- | ---: | --- |",
    ]
    for item in attempts:
        pcvs = "; ".join(f"`{p['name']} = {p['expression']}`" for p in item["pcvs"])
        score = "-" if item["irregularity_percent"] is None else f"{item['irregularity_percent']:.6g}%"
        lines.append(f"| {item['iteration']} | {pcvs} | {score} | {item['outcome']} |")
    (case_root / "case-report.md").write_text("\n".join(lines) + "\n")
    isolation = _read(case_root / "agent_PCVs" / "isolation.json")
    isolation["thread_id"] = agent["thread_id"]
    _write(case_root / "agent_PCVs" / "isolation.json", isolation)
    return report


def _write_benchmark_report(root: Path, suite: str,
                            feedback_mode: str = "full") -> dict[str, Any]:
    rows = [_read(path) for path in sorted(root.glob("*/case-report.json"))]
    aggregate = {
        "cases": len(rows),
        "success": sum(row["status"] == "success" for row in rows),
        "exhausted": sum(row["status"] == "exhausted" for row in rows),
        "never_reached": sum(row["status"] == "never-reached" for row in rows),
        "iterations": sum(row["iterations"] for row in rows),
    }
    report = {
        "suite": suite,
        "protocol": _protocol(feedback_mode),
        "threshold_percent": THRESHOLD_PERCENT,
        "aggregate": aggregate,
        "results": rows,
    }
    _write(root / "full-report.json", report)
    lines = [
        f"# {suite.upper()} {_protocol(feedback_mode)} evaluation", "",
        f"Cases: {aggregate['cases']}; success: {aggregate['success']}; "
        f"exhausted: {aggregate['exhausted']}; never reached: "
        f"{aggregate['never_reached']}; iterations: {aggregate['iterations']}.", "",
        "| case | status | iterations | best irregularity |", "| --- | --- | ---: | ---: |",
    ]
    csv_rows = []
    for row in rows:
        scores = [a["irregularity_percent"] for a in row["attempts"]
                  if isinstance(a.get("irregularity_percent"), (int, float))]
        best = min(scores) if scores else None
        text = "-" if best is None else f"{best:.6g}%"
        lines.append(f"| {row['case']} | {row['status']} | {row['iterations']} | {text} |")
        csv_rows.append({"case": row["case"], "status": row["status"],
                         "iterations": row["iterations"], "best_irregularity_percent": best,
                         "agent_PCVs_thread": row.get("agent_PCVs_thread")})
    (root / "full-report.md").write_text("\n".join(lines) + "\n")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]) if csv_rows else
                            ["case", "status", "iterations", "best_irregularity_percent", "agent_PCVs_thread"])
    writer.writeheader()
    writer.writerows(csv_rows)
    (root / "full-report.csv").write_text(stream.getvalue())
    return report


def _record_never_reached(root: Path, suite: str, case_id: str,
                          error: Exception,
                          feedback_mode: str = "full",
                          reason: str = "native workload did not reach the target marker") -> dict[str, Any]:
    case_root = root / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    actual = case_root / "case-actual"
    if not actual.exists():
        subprocess.run(
            [sys.executable, str(core.COLLECT), "export", case_id, str(actual)],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        )
        candidate = actual / core.CANDIDATE_FILE
        if candidate.exists():
            candidate.unlink()
    agent_dir = case_root / "agent_PCVs"
    agent_dir.mkdir(exist_ok=True)
    (agent_dir / "PROMPT.md").write_text(_agent_prompt(feedback_mode))
    _write(agent_dir / "isolation.json", {
        "case_id": case_id,
        "agent_role": "agent_PCVs",
        "fresh_thread_per_case": True,
        "thread_id": None,
        "agent_started": False,
        "measurement_agent": None,
        "feedback_mode": feedback_mode,
        "agent_feedback_schema": _feedback_schema(feedback_mode),
        "agent_model": os.environ.get("DRPERF_AGENT_MODEL", "codex-cli-default"),
        "reason": reason,
    })
    report = {
        "schema_version": 1,
        "case": case_id,
        "status": "never-reached",
        "iterations": 0,
        "threshold_percent": THRESHOLD_PERCENT,
        "comparison": "strictly-less-than",
        "measurement_agent": None,
        "measurement_and_scoring": "not started",
        "feedback_mode": feedback_mode,
        "agent_feedback_schema": _feedback_schema(feedback_mode),
        "agent_model": os.environ.get("DRPERF_AGENT_MODEL", "codex-cli-default"),
        "agent_PCVs_thread": None,
        "fixed_workload_digest": None,
        "attempts": [],
        "reason": reason,
        "error": str(error),
    }
    _write(case_root / "case-report.json", report)
    (case_root / "case-report.md").write_text(
        f"# {case_id} full-feedback result\n\n"
        f"Status: `never-reached`; iterations: 0. Reason: {reason}. "
        "No agent or Dr. Perf run was started.\n"
    )
    (case_root / "README.md").write_text(
        _case_readme(
            case_id,
            _read(actual / "case.json")["source"]["path"],
            feedback_mode,
        )
        + "\nThis case is recorded as `never-reached`; `evaluate_pcvs.sh` is unavailable.\n"
    )
    _write_benchmark_report(root, suite, feedback_mode)
    return report


def run_case(case_id: str, suite: str, root: Path, runtime: Path | None,
             python: str, feedback_mode: str = "full") -> dict[str, Any]:
    _ensure_protocol(root, suite, feedback_mode)
    if suite == "wan":
        if runtime is None:
            raise FullFeedbackError("WAN requires --runtime-template")
        run_dir, case_root = _prepare_wan_case(
            case_id, root, runtime, python, feedback_mode
        )
        measure = wan_suite.measure_case
        timeout = 240.0
    elif suite == "vllm":
        if runtime is None:
            raise FullFeedbackError("vLLM requires --runtime-template")
        run_dir, case_root = _prepare_vllm_case(
            case_id, root, runtime, python, feedback_mode
        )
        timeout = 600.0
    elif suite in generic_suite.PYTHON_SUITES:
        run_dir, case_root = _prepare_generic_case(
            case_id, suite, root, python, feedback_mode
        )
        timeout = 120.0
    else:
        raise FullFeedbackError(f"unsupported suite: {suite}")
    agent = _agent_state(case_root)
    state = core.load_state(run_dir)
    if state["status"] in {"success", "exhausted"}:
        return _write_case_report(run_dir, case_root, agent, feedback_mode)
    if state["status"] not in {"awaiting-selector", "awaiting-measurement"}:
        raise FullFeedbackError(f"ambiguous controller state for {case_id}: {state['status']}")

    latest_report = None
    if agent.get("last_report_iteration"):
        path = case_root / "iterations" / f"iteration-{agent['last_report_iteration']:03d}"
        latest_report = {
            "drperf_full_report": _read(path / "drperf-full-report.json")
            if (path / "drperf-full-report.json").is_file() else None,
            "script_decision": _read(path / "script-decision.json"),
        }

    while True:
        state = core.load_state(run_dir)
        if state["status"] == "awaiting-measurement":
            measured = evaluate_pcvs.measure_candidate(
                suite, run_dir, timeout=timeout
            )
            feedback = measured["feedback"]
            assessment = measured["assessment"]
            latest_report = _publish_iteration(
                run_dir, case_root, feedback, assessment, feedback_mode
            )
            agent["last_report_iteration"] = latest_report["iteration"]
            _save_agent_state(case_root, agent)
            print(json.dumps({"event": "measurement", "case": case_id,
                              "iteration": latest_report["iteration"],
                              "status": feedback["status"],
                              "irregularity_percent": feedback.get("irregularity_percent")}), flush=True)
            if core.load_state(run_dir)["status"] in {"success", "exhausted"}:
                result = _write_case_report(
                    run_dir, case_root, agent, feedback_mode
                )
                _write_benchmark_report(root, suite, feedback_mode)
                return result
            continue

        iteration = state["next_iteration"]
        candidate = agent.get("pending_candidate")
        if not isinstance(candidate, dict) or candidate.get("iteration") != iteration:
            prompt = _turn_prompt(
                case_id,
                run_dir / "selector" / "workspace",
                iteration,
                latest_report,
                feedback_mode,
            )
            agent["turns"] += 1
            (case_root / "agent_PCVs" / f"turn-{agent['turns']:03d}-prompt.md").write_text(prompt)
            thread, candidate = strict_wan._agent_turn(
                case_id=f"{feedback_mode}-feedback-{case_id}", role="agent-PCVs", prompt=prompt,
                schema=strict_wan.CANDIDATE_SCHEMA, turn=agent["turns"],
                thread_id=agent["thread_id"], log_root=case_root / "agent_PCVs" / "events",
            )
            agent["thread_id"] = thread
            agent["pending_candidate"] = candidate
            _save_agent_state(case_root, agent)

        rejected = 0
        while True:
            try:
                normalized = evaluate_pcvs.submit_candidate(run_dir, candidate)
                break
            except (strict_wan.StrictWanError, core.EvaluationError) as exc:
                rejected += 1
                if rejected > 5:
                    raise FullFeedbackError(f"candidate rejection limit exceeded for {case_id}") from exc
                prompt = _rejection_prompt(iteration, str(exc), feedback_mode)
                agent["turns"] += 1
                (case_root / "agent_PCVs" / f"turn-{agent['turns']:03d}-prompt.md").write_text(prompt)
                thread, candidate = strict_wan._agent_turn(
                    case_id=f"{feedback_mode}-feedback-{case_id}", role="agent-PCVs", prompt=prompt,
                    schema=strict_wan.CANDIDATE_SCHEMA, turn=agent["turns"],
                    thread_id=agent["thread_id"], log_root=case_root / "agent_PCVs" / "events",
                )
                agent["thread_id"] = thread
                agent["pending_candidate"] = candidate
                _save_agent_state(case_root, agent)
        print(json.dumps({"event": "candidate", "case": case_id, "iteration": iteration,
                          "pcvs": [{"name": p["name"], "expression": p["expression"]}
                                   for p in normalized["pcvs"]]}), flush=True)
        agent["pending_candidate"] = None
        _save_agent_state(case_root, agent)


def run_benchmark(suite: str, root: Path, runtime: Path | None,
                  python: str, feedback_mode: str = "full") -> dict[str, Any]:
    root = root.resolve()
    _ensure_protocol(root, suite, feedback_mode)
    (root / "AGENT_PCVS_PROMPT.md").write_text(_agent_prompt(feedback_mode))
    results = []
    if suite == "wan":
        cases = wan.list_wan_cases()
    elif suite == "vllm":
        cases = vllm_suite.list_vllm_cases()
    elif suite in generic_suite.SUPPORTED_SUITES:
        cases = generic_suite.list_cases(suite)
    else:
        raise FullFeedbackError(f"unsupported suite: {suite}")
    for case_id in cases:
        print(json.dumps({"event": "case-start", "case": case_id}), flush=True)
        existing_report = root / case_id / "case-report.json"
        if existing_report.is_file() and _read(existing_report).get("status") == "never-reached":
            result = _read(existing_report)
        elif generic_suite.unavailable_reason(suite):
            reason = generic_suite.unavailable_reason(suite)
            assert reason is not None
            result = _record_never_reached(
                root, suite, case_id, generic_suite.GenericSuiteError(reason), feedback_mode,
                reason=reason,
            )
        else:
            try:
                result = run_case(
                    case_id, suite, root, runtime, python, feedback_mode
                )
            except vllm_suite.VllmSuiteError as exc:
                if suite != "vllm" or "native workload validation failed" not in str(exc):
                    raise
                result = _record_never_reached(
                    root, suite, case_id, exc, feedback_mode
                )
        results.append(result)
        print(json.dumps({"event": "case-end", "case": case_id,
                          "status": result["status"], "iterations": result["iterations"]}), flush=True)
    report = _write_benchmark_report(root, suite, feedback_mode)
    return report["aggregate"]


def run_wan(root: Path, runtime: Path, python: str) -> dict[str, Any]:
    return run_benchmark("wan", root, runtime, python)


def run_vllm(root: Path, runtime: Path, python: str) -> dict[str, Any]:
    return run_benchmark("vllm", root, runtime, python)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("wan", "vllm"), default="wan")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--runtime-template", type=Path, required=True)
    parser.add_argument("--python", required=True)
    args = parser.parse_args()
    root = args.root if args.root is not None else DEFAULT_ROOT / args.suite
    try:
        result = run_benchmark(args.suite, root, args.runtime_template, args.python)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (FullFeedbackError, strict_wan.StrictWanError, core.EvaluationError,
            wan.WanStageError, wan_suite.WanSuiteError, vllm_suite.VllmSuiteError,
            OSError, ValueError) as exc:
        print(f"full-feedback: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
