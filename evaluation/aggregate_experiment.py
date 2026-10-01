#!/usr/bin/env python3
"""Combine per-suite PCV reports into one experiment-level report."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any


SUITES = (
    "accidental-quadratic",
    "growth-multifold",
    "v8-interpreter",
    "v8-regexp",
    "vllm",
    "wan",
)


def _write(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def aggregate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    suites = []
    rows = []
    for suite in SUITES:
        candidate = root / suite
        suite_root = candidate if (candidate / "full-report.json").is_file() else None
        path = suite_root / "full-report.json" if suite_root is not None else None
        if path is None:
            suites.append({"suite": suite, "status": "not-reported"})
            continue
        report = json.loads(path.read_text())
        suites.append({
            "suite": suite,
            "status": "reported",
            "source_directory": str(suite_root.relative_to(root)),
            "protocol": report.get("protocol"),
            "aggregate": report.get("aggregate", {}),
        })
        for result in report.get("results", []):
            scores = [
                attempt.get("irregularity_percent")
                for attempt in result.get("attempts", [])
                if isinstance(attempt.get("irregularity_percent"), (int, float))
            ]
            rows.append({
                "suite": suite,
                "case": result.get("case"),
                "status": result.get("status"),
                "iterations": result.get("iterations", 0),
                "best_irregularity_percent": min(scores) if scores else None,
            })
    totals = {
        "reported_suites": sum(item["status"] == "reported" for item in suites),
        "cases": len(rows),
        "success": sum(row["status"] == "success" for row in rows),
        "exhausted": sum(row["status"] == "exhausted" for row in rows),
        "never_reached": sum(row["status"] == "never-reached" for row in rows),
        "iterations": sum(int(row["iterations"] or 0) for row in rows),
    }
    return {"root": str(root), "totals": totals, "suites": suites, "results": rows}


def write_reports(root: Path) -> dict[str, Any]:
    root = root.resolve()
    result = aggregate(root)
    _write(root / "experiment-report.json", result)
    totals = result["totals"]
    lines = [
        "# PCV evaluation report",
        "",
        f"Reported suites: {totals['reported_suites']}/{len(SUITES)}; "
        f"cases: {totals['cases']}; success: {totals['success']}; "
        f"exhausted: {totals['exhausted']}; never reached: "
        f"{totals['never_reached']}; iterations: {totals['iterations']}.",
        "",
        "| suite | case | status | iterations | best irregularity |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in result["results"]:
        best = row["best_irregularity_percent"]
        best_text = "-" if best is None else f"{best:.6g}%"
        lines.append(
            f"| {row['suite']} | {row['case']} | {row['status']} | "
            f"{row['iterations']} | {best_text} |"
        )
    (root / "experiment-report.md").write_text("\n".join(lines) + "\n")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=(
        "suite", "case", "status", "iterations", "best_irregularity_percent",
    ))
    writer.writeheader()
    writer.writerows(result["results"])
    (root / "experiment-report.csv").write_text(stream.getvalue())
    return result


def main(default_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--json", action="store_true", help="also print the report")
    args = parser.parse_args()
    if args.root is None:
        parser.error("--root is required")
    report = write_reports(args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(args.root.resolve() / "experiment-report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
