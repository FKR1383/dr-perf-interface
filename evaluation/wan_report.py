#!/usr/bin/env python3
"""Aggregate WAN evaluation summaries into machine- and human-readable tables."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path
import re
from typing import Any


CASE_RE = re.compile(r"^wan-(\d+)$")
FIELDNAMES = ("case", "status", "iterations", "attempts", "final_pcvs", "final_result")


class ReportError(RuntimeError):
    pass


def _read_summary(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReportError(f"summary is not an object: {path}")
    return value


def _pcvs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _irregularity(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _iteration(value: Any, fallback: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
        return value
    return fallback


def normalize_summary(summary: dict[str, Any], source: Path | None = None) -> dict[str, Any]:
    case = summary.get("case_id")
    if not isinstance(case, str) or not CASE_RE.fullmatch(case):
        location = f" in {source}" if source else ""
        raise ReportError(f"invalid WAN case ID{location}: {case!r}")

    raw_attempts = summary.get("attempts", [])
    if not isinstance(raw_attempts, list):
        raise ReportError(f"attempts is not a list for {case}")
    attempts = []
    for index, raw in enumerate(raw_attempts, 1):
        if not isinstance(raw, dict):
            raise ReportError(f"attempt {index} is not an object for {case}")
        attempts.append({
            "iteration": _iteration(raw.get("iteration"), index),
            "pcvs": _pcvs(raw.get("pcvs")),
            "outcome": str(raw.get("outcome", "pending")),
            "irregularity_percent": _irregularity(raw.get("irregularity_percent")),
        })
    attempts.sort(key=lambda item: item["iteration"])

    success_iteration = summary.get("success_iteration")
    final = None
    if isinstance(success_iteration, int) and not isinstance(success_iteration, bool):
        final = next(
            (item for item in attempts if item["iteration"] == success_iteration),
            None,
        )
    if final is None and attempts:
        final = attempts[-1]

    evaluated = summary.get("iterations_evaluated")
    if not isinstance(evaluated, int) or isinstance(evaluated, bool) or evaluated < 0:
        evaluated = sum(item["outcome"] not in ("pending", "measurement-error") for item in attempts)

    status = summary.get("status", "pending")
    return {
        "case": case,
        "status": str(status),
        "iterations": evaluated,
        "attempts": attempts,
        "final_pcvs": final["pcvs"] if final else [],
        "final_result": {
            "outcome": final["outcome"] if final else "pending",
            "irregularity_percent": final["irregularity_percent"] if final else None,
        },
    }


def collect(suite_root: Path) -> dict[str, Any]:
    suite_root = suite_root.resolve()
    if not suite_root.is_dir():
        raise ReportError(f"suite root is not a directory: {suite_root}")
    rows = []
    seen: dict[str, Path] = {}
    for path in sorted(suite_root.rglob("summary.json")):
        row = normalize_summary(_read_summary(path), path)
        if row["case"] in seen:
            raise ReportError(
                f"duplicate summary for {row['case']}: {seen[row['case']]} and {path}"
            )
        seen[row["case"]] = path
        rows.append(row)
    rows.sort(key=lambda row: (int(CASE_RE.fullmatch(row["case"])[1]), row["case"]))
    return {"schema_version": 1, "cases": rows}


def _percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.6g}%"


def _pcv_text(pcvs: list[str]) -> str:
    return ", ".join(pcvs) if pcvs else "-"


def _attempts_text(attempts: list[dict[str, Any]]) -> str:
    if not attempts:
        return "-"
    return "; ".join(
        f"{attempt['iteration']}:[{_pcv_text(attempt['pcvs'])}]"
        f"|{attempt['outcome']}|{_percent(attempt['irregularity_percent'])}"
        for attempt in attempts
    )


def _final_text(result: dict[str, Any]) -> str:
    return f"{result['outcome']}|{_percent(result['irregularity_percent'])}"


def flat_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "case": row["case"],
            "status": row["status"],
            "iterations": row["iterations"],
            "attempts": _attempts_text(row["attempts"]),
            "final_pcvs": _pcv_text(row["final_pcvs"]),
            "final_result": _final_text(row["final_result"]),
        }
        for row in report["cases"]
    ]


def render_csv(report: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(flat_rows(report))
    return output.getvalue()


def _markdown_cell(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def render_markdown(report: dict[str, Any]) -> str:
    headers = list(FIELDNAMES)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in flat_rows(report):
        lines.append("| " + " | ".join(_markdown_cell(row[name]) for name in headers) + " |")
    return "\n".join(lines) + "\n"


def write_reports(suite_root: Path, output_dir: Path) -> dict[str, Any]:
    report = collect(suite_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "wan-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "wan-report.csv").write_text(render_csv(report))
    (output_dir / "wan-report.md").write_text(render_markdown(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite_root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or args.suite_root
    try:
        report = write_reports(args.suite_root, output_dir)
    except (ReportError, OSError) as exc:
        parser.exit(1, f"wan-report: {exc}\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
