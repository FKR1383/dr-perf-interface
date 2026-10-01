#!/usr/bin/env python3
"""Run the isolated Agent-PCVs/full-Dr.-Perf protocol for one suite or case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import core
import full_feedback
import generic_suite
import strict_wan
import vllm_suite
import wan
import wan_suite


REPO_ROOT = Path(__file__).resolve().parents[1]
ALL_SUITES = ("vllm", "wan", *sorted(generic_suite.SUPPORTED_SUITES))


def _result_root(suite: str, feedback_mode: str) -> Path:
    experiment = (
        "bench_correct_feedback" if feedback_mode == "full"
        else "bench_correct_irregularity"
    )
    return REPO_ROOT / experiment / suite


def _defaults(suite: str, feedback_mode: str) -> tuple[Path, Path | None, Path]:
    if suite == "vllm":
        return (
            _result_root(suite, feedback_mode),
            REPO_ROOT / "third_party" / "vllm-cpu" / "vllm",
            REPO_ROOT / "third_party" / "vllm-cpu" / ".venv" / "bin" / "python",
        )
    if suite in generic_suite.SUPPORTED_SUITES:
        return _result_root(suite, feedback_mode), None, Path(sys.executable)
    raise full_feedback.FullFeedbackError(
        "WAN requires explicit --root, --runtime-template, and --python"
    )


def main(default_feedback: str = "full") -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=ALL_SUITES)
    parser.add_argument(
        "--feedback", choices=("full", "scalar"), default=default_feedback,
        help="feedback exposed to Agent-PCVs after each measurement",
    )
    parser.add_argument("--case", help="run one case; omit to run the complete suite")
    parser.add_argument(
        "--prepare-only", action="store_true",
        help="prepare --case and generate its evaluator without starting Agent-PCVs",
    )
    parser.add_argument("--root", type=Path)
    parser.add_argument("--runtime-template", type=Path)
    parser.add_argument("--python", type=Path)
    args = parser.parse_args()

    try:
        if args.suite != "wan":
            default_root, default_runtime, default_python = _defaults(
                args.suite, args.feedback
            )
            root = (args.root or default_root).resolve()
            runtime_value = args.runtime_template or default_runtime
            runtime = runtime_value.resolve() if runtime_value is not None else None
            python = (args.python or default_python).absolute()
        else:
            if args.root is None or args.runtime_template is None or args.python is None:
                raise full_feedback.FullFeedbackError(
                    "WAN requires --root, --runtime-template, and --python"
                )
            root = args.root.resolve()
            runtime = args.runtime_template.resolve()
            python = args.python.absolute()

        if not python.is_file():
            raise full_feedback.FullFeedbackError(f"Python executable not found: {python}")
        full_feedback._ensure_protocol(root, args.suite, args.feedback)
        if args.prepare_only and not args.case:
            raise full_feedback.FullFeedbackError("--prepare-only requires --case")
        if args.prepare_only:
            if args.suite == "vllm":
                assert runtime is not None
                run_dir, case_root = full_feedback._prepare_vllm_case(
                    args.case, root, runtime, str(python), args.feedback
                )
            elif args.suite == "wan":
                assert runtime is not None
                run_dir, case_root = full_feedback._prepare_wan_case(
                    args.case, root, runtime, str(python), args.feedback
                )
            else:
                if args.suite in generic_suite.V8_SUITES:
                    raise full_feedback.FullFeedbackError(
                        generic_suite.unavailable_reason(args.suite)
                        or "V8 runtime unavailable"
                    )
                run_dir, case_root = full_feedback._prepare_generic_case(
                    args.case, args.suite, root, str(python), args.feedback
                )
            result = {
                "case": args.case,
                "status": core.load_state(run_dir)["status"],
                "agent_started": False,
                "candidate_schema": str(
                    (REPO_ROOT / "evaluation" / "candidate.schema.json").resolve()
                ),
                "evaluator": str((case_root / "evaluate_pcvs.sh").resolve()),
            }
        elif args.case:
            unavailable = generic_suite.unavailable_reason(args.suite)
            if unavailable:
                result = full_feedback._record_never_reached(
                    root, args.suite, args.case,
                    generic_suite.GenericSuiteError(unavailable), args.feedback,
                    reason=unavailable,
                )
            else:
                try:
                    result = full_feedback.run_case(
                        args.case, args.suite, root, runtime, str(python), args.feedback
                    )
                except vllm_suite.VllmSuiteError as exc:
                    if args.suite != "vllm" or "native workload validation failed" not in str(exc):
                        raise
                    result = full_feedback._record_never_reached(
                        root, args.suite, args.case, exc, args.feedback
                    )
            full_feedback._write_benchmark_report(
                root, args.suite, args.feedback
            )
        else:
            result = full_feedback.run_benchmark(
                args.suite, root, runtime, str(python), args.feedback
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (
        full_feedback.FullFeedbackError,
        strict_wan.StrictWanError,
        core.EvaluationError,
        wan.WanStageError,
        wan_suite.WanSuiteError,
        vllm_suite.VllmSuiteError,
        generic_suite.GenericSuiteError,
        OSError,
        ValueError,
    ) as exc:
        print(f"run-agent-pcvs: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
