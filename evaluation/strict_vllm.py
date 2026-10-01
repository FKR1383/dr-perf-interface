#!/usr/bin/env python3
"""Run vLLM cases through the strict blinded two-agent evaluator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import strict_wan as _strict
import vllm_report
import vllm_suite


DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "bench_correct_vllm"


def _prepare_case(case_id: str, root: Path, runtime: Path, python: str) -> Path:
    """Prepare independently so an unreachable earlier case does not block later ones."""
    root = root.resolve()
    if case_id not in vllm_suite.list_vllm_cases():
        raise _strict.StrictWanError(f"unknown vLLM case: {case_id}")
    run_dir = root / case_id
    if not run_dir.exists():
        vllm_suite.prepare_case(
            case_id,
            root,
            runtime,
            python,
            threshold=10.0,
            max_iterations=_strict.MAX_ITERATIONS,
        )
    return run_dir


def _record_unreachable(root: Path, case_id: str, error: Exception) -> dict[str, Any]:
    run_dir = root.resolve() / case_id
    run_dir.mkdir(parents=True, exist_ok=True)
    reason = "native workload passed its value path but did not reach the target marker"
    detail = {
        "schema_version": 1,
        "case_id": case_id,
        "status": "unreachable",
        "reason": reason,
        "error": str(error),
    }
    _strict._write_json(run_dir / "controller" / "vllm-preparation-error.json", detail)
    summary = {
        "schema_version": 1,
        "case_id": case_id,
        "status": "unreachable",
        "threshold_percent": 10.0,
        "comparison": "strictly-less-than",
        "iterations_evaluated": 0,
        "success_iteration": None,
        "attempts": [],
    }
    _strict._write_json(run_dir / "summary.json", summary)
    report = {
        "case": case_id,
        "status": "unreachable",
        "iterations": 0,
        "attempts": [],
        "reason": reason,
    }
    _strict._write_json(run_dir / "report.json", report)
    (run_dir / "report.md").write_text(
        "| case | status | iterations | reason |\n"
        "| --- | --- | ---: | --- |\n"
        f"| {case_id} | unreachable | 0 | {reason} |\n"
    )
    return report


def _run_all(root: Path, runtime: Path, python: str) -> dict[str, Any]:
    results = []
    root = root.resolve()
    for case_id in vllm_suite.list_vllm_cases():
        summary_path = root / case_id / "summary.json"
        if summary_path.is_file():
            summary = _strict._json(summary_path)
            if summary.get("status") == "unreachable":
                results.append(_strict._json(root / case_id / "report.json"))
                continue
        try:
            results.append(_strict.run_case(case_id, root, runtime, python))
        except vllm_suite.VllmSuiteError as exc:
            if "native workload validation failed" not in str(exc):
                raise
            results.append(_record_unreachable(root, case_id, exc))
        vllm_report.write_reports(root, root)

    report = vllm_report.write_reports(root, root)
    (root / "full-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (root / "full-report.md").write_text(vllm_report.render_markdown(report))
    (root / "full-report.csv").write_text(vllm_report.render_csv(report))
    return {
        "cases": len(results),
        "unreachable": sum(item.get("status") == "unreachable" for item in results),
        "status": "complete",
    }


_strict.DEFAULT_ROOT = DEFAULT_ROOT
_strict.wan.list_wan_cases = vllm_suite.list_vllm_cases
_strict.wan_suite = vllm_suite
_strict.wan_report = vllm_report
_strict.prepare_case = _prepare_case
_strict.run_all = _run_all


if __name__ == "__main__":
    raise SystemExit(_strict.main())
