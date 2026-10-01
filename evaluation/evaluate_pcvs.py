#!/usr/bin/env python3
"""Evaluate one Agent-PCVs candidate through the trusted Dr. Perf pipeline.

This program never launches an agent.  It accepts the structured response from
an Agent-PCVs session, validates and applies its expressions, snapshots the
annotation, runs Dr. Perf, and prints the complete machine-readable result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import core
import generic_suite
import strict_wan
import vllm_suite
import wan_suite


class PcvEvaluatorError(RuntimeError):
    pass


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def _measurement_payload(run_dir: Path) -> dict[str, Any]:
    state = core.load_state(run_dir)
    attempt = state["attempts"][-1]
    measurement = attempt["measurement_runs"][-1]
    measurement_dir = run_dir / attempt["path"] / measurement["path"]
    metrics_path = measurement_dir / "metrics.json"
    metrics = _read(metrics_path) if metrics_path.is_file() else None
    return {
        "schema_version": 1,
        "case_id": state["case_id"],
        "iteration": attempt["iteration"],
        "candidate": attempt["candidate"],
        "drperf_full_report": metrics,
        "feedback": state["last_feedback"],
        "assessment": measurement["assessment"],
        "decision": {
            "status": state["status"],
            "success": bool(measurement["assessment"].get("success")),
            "threshold_percent": state["threshold_percent"],
            "comparison": state["comparison"],
            "irregularity_percent": measurement["assessment"].get(
                "irregularity_percent"
            ),
        },
    }


def submit_candidate(run_dir: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate/apply a candidate and transition the case to measurement."""
    run_dir = run_dir.resolve()
    state = core.load_state(run_dir)
    if state["status"] != "awaiting-selector":
        raise PcvEvaluatorError(
            f"cannot accept PCVs while case status is {state['status']}"
        )
    normalized = strict_wan._apply_candidate(
        run_dir, candidate, state["next_iteration"]
    )
    core.submit(run_dir)
    return normalized


def measure_candidate(
    suite: str, run_dir: Path, *, timeout: float | None = None
) -> dict[str, Any]:
    """Run Dr. Perf for the already-submitted candidate and return full output."""
    run_dir = run_dir.resolve()
    state = core.load_state(run_dir)
    if state["status"] != "awaiting-measurement":
        raise PcvEvaluatorError(
            f"cannot measure while case status is {state['status']}"
        )
    case_id = state["case_id"]
    suite_root = run_dir.parent
    if suite == "vllm":
        measure = vllm_suite.measure_case
        effective_timeout = 600.0 if timeout is None else timeout
    elif suite == "wan":
        measure = wan_suite.measure_case
        effective_timeout = 240.0 if timeout is None else timeout
    elif suite in generic_suite.PYTHON_SUITES:
        effective_timeout = 120.0 if timeout is None else timeout
        feedback, assessment = generic_suite.measure_case(
            run_dir, timeout=effective_timeout
        )
        if feedback["status"] == "measurement-error":
            raise PcvEvaluatorError(
                f"measurement infrastructure failed for {case_id}"
            )
        return _measurement_payload(run_dir)
    else:
        raise PcvEvaluatorError(f"unsupported suite: {suite}")

    feedback, assessment = measure(
        suite_root, case_id, timeout=effective_timeout
    )
    if feedback["status"] == "measurement-error":
        recovered = vllm_suite._consume_marker_expression_error(run_dir)
        if recovered is None:
            raise PcvEvaluatorError(
                f"measurement infrastructure failed for {case_id}"
            )
    return _measurement_payload(run_dir)


def evaluate_candidate(
    suite: str,
    run_dir: Path,
    candidate: dict[str, Any] | None,
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Submit PCVs when needed, run Dr. Perf, and return the complete result."""
    run_dir = run_dir.resolve()
    state = core.load_state(run_dir)
    normalized = None
    if state["status"] == "awaiting-selector":
        if candidate is None:
            raise PcvEvaluatorError("candidate JSON is required while awaiting PCVs")
        normalized = submit_candidate(run_dir, candidate)
    elif state["status"] == "awaiting-measurement":
        if candidate is not None:
            submitted = state["attempts"][-1]["candidate"]
            checked = core.validate_candidate(
                candidate,
                state["attempts"][-1]["iteration"],
                state["max_pcvs"],
            )
            if checked != submitted:
                raise PcvEvaluatorError(
                    "case already has a different submitted candidate awaiting measurement"
                )
            normalized = submitted
    else:
        raise PcvEvaluatorError(
            f"case is not evaluable while status is {state['status']}"
        )

    result = measure_candidate(suite, run_dir, timeout=timeout)
    result["accepted_candidate"] = normalized or result["candidate"]
    return result


def _candidate(path: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = _read(Path(path))
    if not isinstance(value, dict):
        raise PcvEvaluatorError("candidate must be one JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        choices=("vllm", "wan", *sorted(generic_suite.PYTHON_SUITES)),
        required=True,
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--candidate",
        help="Agent-PCVs response JSON file, or '-' for stdin; omit only to resume measurement",
    )
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args()
    try:
        result = evaluate_candidate(
            args.suite,
            args.run_dir,
            _candidate(args.candidate),
            timeout=args.timeout,
        )
    except (
        PcvEvaluatorError,
        strict_wan.StrictWanError,
        core.EvaluationError,
        generic_suite.GenericSuiteError,
        vllm_suite.VllmSuiteError,
        wan_suite.WanSuiteError,
        OSError,
        ValueError,
    ) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "result": result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
