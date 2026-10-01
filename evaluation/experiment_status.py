#!/usr/bin/env python3
"""Read-only status display for a scripted PCV experiment root."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import core
import generic_suite
import vllm_suite
import wan


def _case_ids(suite: str) -> list[str]:
    if suite == "vllm":
        return vllm_suite.list_vllm_cases()
    if suite == "wan":
        return wan.list_wan_cases()
    if suite in generic_suite.SUPPORTED_SUITES:
        return generic_suite.list_cases(suite)
    raise ValueError(f"unsupported suite: {suite}")


def collect(root: Path, suite: str) -> dict[str, Any]:
    root = root.resolve()
    rows = []
    for case_id in _case_ids(suite):
        report_path = root / case_id / "case-report.json"
        state_path = root / ".controller-runs" / case_id / "controller" / "state.json"
        if report_path.is_file():
            report = json.loads(report_path.read_text())
            rows.append({
                "case": case_id,
                "status": report["status"],
                "iterations": report["iterations"],
                "next_iteration": None,
                "last_irregularity_percent": (
                    report["attempts"][-1].get("irregularity_percent")
                    if report.get("attempts") else None
                ),
            })
        elif state_path.is_file():
            state = core.load_state(state_path.parents[1])
            rows.append({
                "case": case_id,
                "status": state["status"],
                "iterations": len(state.get("attempts", [])),
                "next_iteration": state.get("next_iteration"),
                "last_irregularity_percent": (
                    state.get("last_feedback") or {}
                ).get("irregularity_percent"),
            })
        else:
            rows.append({
                "case": case_id,
                "status": "not-started",
                "iterations": 0,
                "next_iteration": 1,
                "last_irregularity_percent": None,
            })
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {
        "root": str(root),
        "suite": suite,
        "counts": counts,
        "iterations": sum(row["iterations"] for row in rows),
        "cases": rows,
    }


def main(default_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument(
        "--suite",
        choices=("vllm", "wan", *sorted(generic_suite.SUPPORTED_SUITES)),
        default="vllm",
    )
    parser.add_argument("--all", action="store_true", help="show terminal cases too")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.root is None:
        parser.error("--root is required")
    result = collect(args.root, args.suite)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    print(f"root: {result['root']}")
    print(f"suite: {result['suite']}")
    print("counts: " + ", ".join(
        f"{key}={value}" for key, value in sorted(result["counts"].items())
    ))
    print(f"iterations: {result['iterations']}")
    visible = result["cases"] if args.all else [
        row for row in result["cases"]
        if row["status"] not in {
            "success", "exhausted", "never-reached", "not-started"
        }
    ]
    if visible:
        print("case\tstatus\titerations\tnext\tlast_irregularity_percent")
        for row in visible:
            print(
                f"{row['case']}\t{row['status']}\t{row['iterations']}\t"
                f"{row['next_iteration'] if row['next_iteration'] is not None else '-'}\t"
                f"{row['last_irregularity_percent'] if row['last_irregularity_percent'] is not None else '-'}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
