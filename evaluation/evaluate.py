#!/usr/bin/env python3
"""Manual two-role evaluation loop for Dr. Perf PCV discovery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import core


def dump(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="action", required=True)

    sub.add_parser("list", help="list clean cases that also occur in bench_anontated")

    start = sub.add_parser("start", help="create a blinded evaluation run")
    start.add_argument("case")
    start.add_argument("run_dir", type=Path)
    start.add_argument("--threshold", type=float, default=10.0, help="success threshold in percent")
    start.add_argument("--max-iterations", type=int)
    start.add_argument("--max-pcvs", type=int, default=4)
    start.add_argument("--python", default=sys.executable)
    start.add_argument("--d8")

    submit = sub.add_parser("submit", help="snapshot Agent 1's current candidate")
    submit.add_argument("run_dir", type=Path)

    measure = sub.add_parser("measure", help="run Agent 2's Dr. Perf measurement")
    measure.add_argument("run_dir", type=Path)
    measure.add_argument("--timeout", type=float, default=120.0)
    measure.add_argument("command", nargs=argparse.REMAINDER)

    status = sub.add_parser("status", help="show the public run summary")
    status.add_argument("run_dir", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.action == "list":
            for item in core.available_cases():
                print(
                    f"{item['id']:24} {item['language']:8} {item['test_status']:16} "
                    f"{item['group']}/{item['title']}"
                )
            return 0
        if args.action == "start":
            state = core.start(
                args.case,
                args.run_dir,
                threshold_percent=args.threshold,
                max_iterations=args.max_iterations,
                max_pcvs=args.max_pcvs,
                python=args.python,
                d8=args.d8,
            )
            dump({
                "case": state["case_id"],
                "status": state["status"],
                "selector_directory": str(args.run_dir.resolve() / "selector"),
                "selector_prompt": str(args.run_dir.resolve() / "selector" / "PROMPT.md"),
            })
            return 0
        if args.action == "submit":
            dump(core.submit(args.run_dir))
            return 0
        if args.action == "measure":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            feedback, _ = core.measure(
                args.run_dir,
                timeout=args.timeout,
                command_override=command or None,
            )
            dump(feedback)
            return 0 if feedback["status"] != "measurement-error" else 2
        if args.action == "status":
            dump(core.read_json(args.run_dir.resolve() / "summary.json"))
            return 0
    except (core.EvaluationError, OSError, ValueError) as exc:
        print(f"evaluation: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

