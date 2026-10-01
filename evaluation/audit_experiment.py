#!/usr/bin/env python3
"""Audit agent isolation and feedback visibility without running a benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import strict_wan


def _reports(root: Path) -> list[dict]:
    return [
        json.loads(path.read_text())
        for path in sorted(root.glob("*-*/case-report.json"))
    ]


def _thread_ids(root: Path, reports: list[dict]) -> list[str]:
    threads = [
        report.get("agent_PCVs_thread") for report in reports
        if report.get("agent_PCVs_thread")
    ]
    for path in sorted(root.glob("*-*/agent_PCVs/state.json")):
        thread = json.loads(path.read_text()).get("thread_id")
        if thread and thread not in threads:
            threads.append(thread)
    return threads


def _workload_digests(root: Path, reports: list[dict]) -> dict[str, str]:
    result = {
        report["case"]: report["fixed_workload_digest"]
        for report in reports
        if report.get("fixed_workload_digest")
    }
    for path in sorted(root.glob("*-*/agent_PCVs/isolation.json")):
        receipt = json.loads(path.read_text())
        case = receipt.get("case_id")
        digest = receipt.get("fixed_workload_digest")
        if case and digest:
            result[case] = digest
    return result


def audit(root: Path, feedback_mode: str, counterpart: Path | None) -> dict:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    receipts = []
    for path in sorted(root.glob("*-*/agent_PCVs/isolation.json")):
        receipt = json.loads(path.read_text())
        receipts.append(receipt)
        case = receipt.get("case_id", path.parents[1].name)
        if receipt.get("measurement_agent") is not None:
            errors.append(f"{case}: measurement_agent is not null")
        if receipt.get("feedback_mode") not in (None, feedback_mode):
            errors.append(f"{case}: feedback mode mismatch")
        disabled = set(receipt.get("tools_disabled", []))
        missing = set(strict_wan.DISABLED_FEATURES) - disabled
        if missing and receipt.get("agent_started", True):
            errors.append(f"{case}: missing disabled tools {sorted(missing)}")
    reports = _reports(root)
    threads = _thread_ids(root, reports)
    if len(threads) != len(set(threads)):
        errors.append("agent thread ID reused within experiment")

    unexpected_items = []
    for path in sorted(root.glob("*-*/agent_PCVs/events/*.events.jsonl")):
        for line in path.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                unexpected_items.append(f"{path}: non-JSON event")
                continue
            if event.get("type") == "item.completed":
                item_type = event.get("item", {}).get("type")
                if item_type not in {"agent_message", "reasoning", "error"}:
                    unexpected_items.append(f"{path}: {item_type}")
    errors.extend(unexpected_items)

    if feedback_mode == "scalar":
        protocol_path = root / "experiment-protocol.json"
        if protocol_path.is_file():
            protocol = json.loads(protocol_path.read_text())
            if protocol.get("agent_feedback_schema") != "score-or-sanitized-invalid-v2":
                errors.append(f"{protocol_path}: not scalar feedback schema v2")
        forbidden = (
            '"drperf_full_report"', '"states"', '"formula"',
            '"coefficients"', '"gate_reasons"', '"script_decision"',
        )
        for path in sorted(root.glob("*-*/agent_PCVs/turn-*-prompt.md")):
            text = path.read_text(errors="replace")
            if (
                "Previous irregularity:" not in text
                and "The previous measurement was invalid." not in text
            ):
                continue
            hits = [token for token in forbidden if token in text]
            if hits:
                errors.append(f"{path}: scalar retry leaked {hits}")
        for path in sorted(root.glob("*-*/iterations/*/agent-visible-feedback.json")):
            value = json.loads(path.read_text())
            keys = set(value) if isinstance(value, dict) else set()
            numeric = keys == {"irregularity_percent"} and isinstance(
                value.get("irregularity_percent"), (int, float)
            )
            invalid = (
                keys == {"status", "reasons"}
                and value.get("status") == "invalid"
                and isinstance(value.get("reasons"), list)
                and bool(value["reasons"])
            )
            if not (numeric or invalid):
                errors.append(f"{path}: non-scalar agent-visible feedback")
            decision_path = path.with_name("script-decision.json")
            if numeric and decision_path.is_file():
                assessment = json.loads(decision_path.read_text()).get("assessment", {})
                if (
                    assessment.get("valid") is False
                    and value.get("irregularity_percent") == 100.0
                ):
                    errors.append(
                        f"{path}: legacy fake 100% feedback for invalid measurement"
                    )

    overlap = []
    workload_mismatches = []
    if counterpart is not None and counterpart.exists():
        other_root = counterpart.resolve()
        other_reports = _reports(other_root)
        other_threads = set(_thread_ids(other_root, other_reports))
        overlap = sorted(set(threads) & other_threads)
        if overlap:
            errors.append(f"thread IDs overlap counterpart: {overlap}")
        own_digests = _workload_digests(root, reports)
        other_digests = _workload_digests(other_root, other_reports)
        for case in sorted(set(own_digests) & set(other_digests)):
            if own_digests[case] != other_digests[case]:
                workload_mismatches.append(case)
        if workload_mismatches:
            errors.append(f"workload digest mismatch: {workload_mismatches}")
    return {
        "root": str(root),
        "feedback_mode": feedback_mode,
        "receipts": len(receipts),
        "reports": len(reports),
        "threads": len(threads),
        "unique_threads": len(set(threads)),
        "counterpart_thread_overlap": overlap,
        "counterpart_workload_mismatches": workload_mismatches,
        "warnings": warnings,
        "errors": errors,
        "ok": not errors,
    }


def main(default_root: Path | None = None,
         default_feedback: str | None = None,
         default_counterpart: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--feedback", choices=("full", "scalar"), default=default_feedback)
    parser.add_argument("--counterpart", type=Path, default=default_counterpart)
    args = parser.parse_args()
    if args.root is None or args.feedback is None:
        parser.error("--root and --feedback are required")
    result = audit(args.root, args.feedback, args.counterpart)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
