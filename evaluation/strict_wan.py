#!/usr/bin/env python3
"""Sequential WAN evaluation with fresh, tool-free agents per benchmark."""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import core
import wan
import wan_report
import wan_suite


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / "bench_correct"
MAX_ITERATIONS = 10
CANDIDATE_SCHEMA = Path(__file__).with_name("candidate.schema.json")
SCORE_SCHEMA = Path(__file__).with_name("irregularity.schema.json")
STRICT_STATE = "strict-state.json"
DISABLED_FEATURES = (
    "shell_tool",
    "unified_exec",
    "browser_use",
    "browser_use_external",
    "apps",
    "computer_use",
    "image_generation",
    "view_image",
    "standalone_web_search",
    "plugins",
    "skill_search",
)
FORBIDDEN_CALLS = {
    "open", "exec", "eval", "compile", "globals", "locals",
    "vars", "setattr", "delattr", "breakpoint", "input", "help",
}
ALLOWED_METHOD_CALLS = {
    "numel", "dim", "size", "stride", "is_contiguous", "count", "get", "item",
    "__sizeof__", "get_count",
}


class StrictWanError(RuntimeError):
    pass


def _json(path: Path) -> Any:
    return json.loads(path.read_text())


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _agent_cwd(case_id: str, role: str, *, reset: bool = False) -> Path:
    path = Path(tempfile.gettempdir()) / "drperf-strict-agents" / case_id / role
    if reset and path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _codex_base(schema: Path) -> list[str]:
    command = [
        "codex", "exec", "--ignore-user-config", "--ignore-rules",
        "--skip-git-repo-check", "--json", "--output-schema", str(schema.resolve()),
        "-c", 'web_search="disabled"',
    ]
    model = os.environ.get("DRPERF_AGENT_MODEL")
    if model:
        command.extend(("--model", model))
    for feature in DISABLED_FEATURES:
        command.extend(("--disable", feature))
    return command


def _parse_codex_events(stdout: str) -> tuple[str | None, dict[str, Any]]:
    thread_id = None
    messages: list[str] = []
    for raw in stdout.splitlines():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StrictWanError(f"non-JSON Codex event: {raw[:200]!r}") from exc
        event_type = event.get("type")
        if event_type == "thread.started":
            thread_id = event.get("thread_id")
        if event_type == "item.completed":
            item = event.get("item", {})
            item_type = item.get("type")
            if item_type == "agent_message":
                messages.append(str(item.get("text", "")))
            elif item_type not in {"reasoning", "error"}:
                raise StrictWanError(f"isolated agent attempted a non-message action: {item_type}")
    if not messages:
        raise StrictWanError("isolated agent returned no structured message")
    try:
        payload = json.loads(messages[-1])
    except json.JSONDecodeError as exc:
        raise StrictWanError("isolated agent response is not JSON") from exc
    if not isinstance(payload, dict):
        raise StrictWanError("isolated agent response must be a JSON object")
    return thread_id, payload


def _agent_turn(
    *,
    case_id: str,
    role: str,
    prompt: str,
    schema: Path,
    turn: int,
    thread_id: str | None,
    log_root: Path,
) -> tuple[str, dict[str, Any]]:
    cwd = _agent_cwd(case_id, role, reset=thread_id is None)
    if thread_id is None:
        command = [*_codex_base(schema), "-"]
    else:
        base = _codex_base(schema)
        command = [base[0], base[1], "resume", *base[2:], thread_id, "-"]
    result = subprocess.run(
        command,
        cwd=cwd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=900,
    )
    log_root.mkdir(parents=True, exist_ok=True)
    (log_root / f"turn-{turn:03d}.events.jsonl").write_text(result.stdout)
    (log_root / f"turn-{turn:03d}.stderr.txt").write_text(result.stderr)
    if result.returncode:
        raise StrictWanError(
            f"{role} failed for {case_id}: returncode={result.returncode}; "
            f"stderr={result.stderr[-1000:]!r}"
        )
    new_thread, payload = _parse_codex_events(result.stdout)
    identity = thread_id or new_thread
    if not isinstance(identity, str) or not identity:
        raise StrictWanError(f"{role} did not provide a persistent thread ID")
    if thread_id is not None and new_thread not in (None, thread_id):
        raise StrictWanError(f"{role} unexpectedly changed thread identity")
    return identity, payload


def _file_blocks(workspace: Path) -> str:
    manifest = _json(workspace / "case.json")
    paths = [Path(manifest["source"]["path"])]
    paths.extend(Path(value) for value in manifest["tests"]["files"])
    paths.extend((Path("TASK.md"), Path("case.json")))
    blocks = []
    for relative in paths:
        path = workspace / relative
        if not path.is_file():
            raise StrictWanError(f"missing isolated benchmark file: {relative}")
        blocks.append(f"\n--- FILE: {relative.as_posix()} ---\n{path.read_text(errors='replace')}")
    return "".join(blocks)


def _selector_initial_prompt(case_id: str, workspace: Path) -> str:
    return f"""You are Agent 1 for exactly one benchmark: {case_id}.

This conversation persists for every attempt of this benchmark and will never be
reused for another benchmark. You have no tools. The text below is the complete
sanitized benchmark context. Existing PCV annotations and previous results have
been removed. Never request or infer Dr. Perf internals. Select 1-4 cheap state
expressions available when the marked region is entered that explain instruction
count. Any cheap mathematical derivation of entry state is allowed, such as
products, powers, comparisons, conditional expressions, and cardinalities;
runtime/library state is also allowed. Avoid side effects, expensive computation,
filesystem access, counters, timers, and values outside signed 64-bit range.

Return only the candidate JSON required by the schema, with iteration 1.
Success requires irregularity strictly below 10%. On later turns you receive
only the previous numeric irregularity and must retain your own attempt context.

SANITIZED BENCHMARK:{_file_blocks(workspace)}
"""


def _selector_retry_prompt(iteration: int, irregularity: float) -> str:
    return (
        f"Previous irregularity: {irregularity:.12g}%. "
        f"Return only a replacement candidate JSON for iteration {iteration}. "
        "Use your retained benchmark and attempt context. Success is strictly below 10%."
    )


def _selector_rejection_prompt(iteration: int, reason: str) -> str:
    return (
        f"Your iteration {iteration} candidate was rejected before submission: {reason}. "
        f"Return only a replacement candidate JSON for iteration {iteration}. "
        "Stay within the fixed expression policy. No benchmark attempt was consumed."
    )


def _validate_expression(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise StrictWanError(f"invalid PCV expression {expression!r}: {exc}") from exc
    for node in ast.walk(tree):
        if isinstance(node, (ast.Lambda, ast.NamedExpr, ast.Await, ast.Yield, ast.YieldFrom)):
            raise StrictWanError(f"side-effect-capable PCV expression is forbidden: {expression}")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_CALLS:
            raise StrictWanError(f"forbidden name in PCV expression: {node.id}")
        if (
            isinstance(node, ast.Attribute)
            and node.attr.startswith("__")
            and node.attr not in {"__dict__", "__sizeof__"}
        ):
            raise StrictWanError("dunder attribute access is forbidden in PCV expressions")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == "__import__":
                    if (
                        len(node.args) != 1
                        or node.keywords
                        or not isinstance(node.args[0], ast.Constant)
                        or node.args[0].value not in {"gc", "sys"}
                    ):
                        raise StrictWanError("only exact gc or sys runtime-state imports are allowed")
                elif node.func.id not in {
                    "len", "int", "float", "bool", "max", "min", "sum", "abs", "range",
                    "isinstance", "hash", "getattr",
                }:
                    raise StrictWanError(f"forbidden PCV function call: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr not in ALLOWED_METHOD_CALLS:
                    raise StrictWanError(f"forbidden PCV method call: {node.func.attr}")
            else:
                raise StrictWanError("indirect calls are forbidden in PCV expressions")
    return ast.unparse(tree.body)


def _apply_candidate(run_dir: Path, candidate: dict[str, Any], iteration: int) -> dict[str, Any]:
    state = core.load_state(run_dir)
    candidate = core.validate_candidate(candidate, iteration, state["max_pcvs"])
    normalized = json.loads(json.dumps(candidate))
    for pcv in normalized["pcvs"]:
        pcv["expression"] = _validate_expression(pcv["expression"])

    workspace = run_dir / "selector" / "workspace"
    source_path = workspace / state["source_path"]
    empty = wan.strip_marker_keywords(source_path.read_bytes(), state["case_id"])
    tree = ast.parse(empty)
    call = wan._target_marker(tree, state["case_id"])
    lines = empty.splitlines(keepends=True)
    end = wan._byte_offset(lines, call.end_lineno, call.end_col_offset)
    keywords = ", " + ", ".join(
        f"{pcv['name']}=({pcv['expression']})" for pcv in normalized["pcvs"]
    )
    annotated = empty[: end - 1] + keywords.encode() + b")" + empty[end:]
    # ``ast.parse`` does not run symbol-table validation, so it misses invalid
    # annotations such as reading a name before a later ``global`` statement.
    # Compile the candidate before submission so these remain rejected Agent 1
    # turns instead of being misclassified as measurement infrastructure errors.
    try:
        compile(annotated, str(source_path), "exec")
    except SyntaxError as exc:
        raise StrictWanError(f"candidate annotation does not compile: {exc.msg}") from exc
    source_path.write_bytes(annotated)
    core.write_json(workspace / core.CANDIDATE_FILE, normalized)
    return normalized


def _measurement_payload(run_dir: Path) -> dict[str, Any]:
    state = core.load_state(run_dir)
    attempt = state["attempts"][-1]
    measurement = attempt["measurement_runs"][-1]
    metrics = _json(run_dir / attempt["path"] / measurement["path"] / "metrics.json")
    return {
        "case_id": state["case_id"],
        "iteration": attempt["iteration"],
        "returncode": metrics.get("returncode"),
        "validity_warnings": metrics.get("validity_warnings", []),
        "pcv_names": metrics.get("pcv_names"),
        "distinct_states": metrics.get("distinct_states"),
        "required_states": metrics.get("required_states"),
        "dropped_calls": metrics.get("dropped_calls"),
        "nested_calls_per_call": metrics.get("nested_calls_per_call"),
        "states": [
            {
                "state": row.get("state"),
                "unexplained_share": row.get("unexplained_share"),
            }
            for row in metrics.get("states", [])
        ],
    }


def _measurer_prompt(payload: dict[str, Any], first: bool) -> str:
    prefix = """You are Agent 2 for exactly one benchmark. This conversation is
never reused for another benchmark. A trusted executor ran Dr. Perf for you.
You must not propose PCVs. Validate that the measurement is scoreable. For a
scoreable result, calculate irregularity_percent as 100 times the maximum
unexplained_share across states. For an unscoreable result, return the fixed
numeric penalty 100.0. Return only the schema JSON. Success is strictly less
than 10%.\n\n""" if first else """Next Dr. Perf result for the same benchmark. Return only the
schema JSON; do not propose PCVs. Use the fixed numeric penalty 100.0 if the
result is unscoreable.\n\n"""
    return prefix + json.dumps(payload, indent=2, sort_keys=True)


def _case_report(run_dir: Path, strict: dict[str, Any]) -> None:
    summary = _json(run_dir / "summary.json")
    attempts = []
    for item in summary["attempts"]:
        feedback_by_iteration = strict.get("feedback_by_iteration", {})
        attempts.append({
            "iteration": item["iteration"],
            "pcvs": item["pcvs"],
            "outcome": item["outcome"],
            "irregularity_percent": item["irregularity_percent"],
            "agent_1_feedback_percent": feedback_by_iteration.get(str(item["iteration"])),
        })
    report = {
        "case": summary["case_id"],
        "status": summary["status"],
        "iterations": summary["iterations_evaluated"],
        "agent_1_thread": strict["agent_1_thread"],
        "agent_2_thread": strict["agent_2_thread"],
        "attempts": attempts,
    }
    _write_json(run_dir / "report.json", report)
    lines = [
        "| case | status | iterations | agent_1 | agent_2 |",
        "| --- | --- | ---: | --- | --- |",
        f"| {report['case']} | {report['status']} | {report['iterations']} | "
        f"{report['agent_1_thread']} | {report['agent_2_thread']} |",
        "",
        "| iteration | PCVs | Dr. Perf irregularity | Agent 1 feedback | outcome |",
        "| ---: | --- | ---: | ---: | --- |",
    ]
    for item in attempts:
        irregularity = item["irregularity_percent"]
        score = "-" if irregularity is None else f"{irregularity:.6g}%"
        feedback = item["agent_1_feedback_percent"]
        feedback_text = "-" if feedback is None else f"{feedback:.6g}%"
        lines.append(
            f"| {item['iteration']} | {', '.join(item['pcvs'])} | {score} | "
            f"{feedback_text} | {item['outcome']} |"
        )
    (run_dir / "report.md").write_text("\n".join(lines) + "\n")


def _strict_state(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "controller" / STRICT_STATE
    if path.is_file():
        return _json(path)
    return {
        "schema_version": 1,
        "case_id": run_dir.name,
        "agent_1_thread": None,
        "agent_2_thread": None,
        "agent_1_turns": 0,
        "agent_2_turns": 0,
        "feedback_by_iteration": {},
        "last_agent_1_feedback_percent": None,
    }


def _save_strict(run_dir: Path, value: dict[str, Any]) -> None:
    _write_json(run_dir / "controller" / STRICT_STATE, value)


def _recover_pending_candidate(run_dir: Path, strict: dict[str, Any]) -> dict[str, Any] | None:
    state = core.load_state(run_dir)
    if state["status"] != "awaiting-selector" or strict["agent_1_turns"] < 1:
        return None
    path = run_dir / "agents" / "agent-1" / f"turn-{strict['agent_1_turns']:03d}.events.jsonl"
    if not path.is_file():
        raise StrictWanError("pending Agent 1 turn has no event log")
    thread, candidate = _parse_codex_events(path.read_text())
    if thread != strict["agent_1_thread"]:
        raise StrictWanError("pending Agent 1 candidate has the wrong thread identity")
    if candidate.get("iteration") != state["next_iteration"]:
        return None
    return candidate


def _score_last_attempt(run_dir: Path, strict: dict[str, Any]) -> tuple[float, bool]:
    state = core.load_state(run_dir)
    attempt = state["attempts"][-1]
    if not attempt["measurement_runs"]:
        raise StrictWanError("submitted attempt has no measurement to score")
    assessment = attempt["measurement_runs"][-1]["assessment"]
    payload = _measurement_payload(run_dir)
    strict["agent_2_turns"] += 1
    thread, score = _agent_turn(
        case_id=state["case_id"],
        role="agent-2",
        prompt=_measurer_prompt(payload, strict["agent_2_thread"] is None),
        schema=SCORE_SCHEMA,
        turn=strict["agent_2_turns"],
        thread_id=strict["agent_2_thread"],
        log_root=run_dir / "agents" / "agent-2",
    )
    strict["agent_2_thread"] = thread
    trusted_value = assessment.get("irregularity_percent")
    scoreable = bool(assessment.get("valid")) and isinstance(trusted_value, (int, float))
    expected = float(trusted_value) if scoreable else 100.0
    measured = float(score["irregularity_percent"])
    if scoreable and abs(measured - expected) > 1e-6:
        raise StrictWanError(
            f"Agent 2 score mismatch for {state['case_id']}: agent={measured}, expected={expected}"
        )
    expected_success = scoreable and expected < 10.0
    if scoreable and score["success"] is not expected_success:
        raise StrictWanError(f"Agent 2 applied the threshold incorrectly for {state['case_id']}")
    if not scoreable and (abs(measured - expected) > 1e-6 or score["success"] is not False):
        strict.setdefault("normalized_unscoreable_turns", []).append(attempt["iteration"])
    strict.setdefault("feedback_by_iteration", {})[str(attempt["iteration"])] = expected
    strict["last_agent_1_feedback_percent"] = expected
    _save_strict(run_dir, strict)
    _case_report(run_dir, strict)
    return expected, expected_success


def prepare_case(case_id: str, root: Path, runtime: Path, python: str) -> Path:
    root = root.resolve()
    cases = wan.list_wan_cases()
    if case_id not in cases:
        raise StrictWanError(f"unknown WAN case: {case_id}")
    index = cases.index(case_id)
    for earlier in cases[:index]:
        prior = root / earlier / "summary.json"
        if not prior.is_file() or _json(prior).get("status") not in {"success", "exhausted"}:
            raise StrictWanError(f"cannot start {case_id} before {earlier} is terminal")
    run_dir = root / case_id
    if not run_dir.exists():
        wan_suite.prepare_case(
            case_id,
            root,
            runtime,
            python,
            threshold=10.0,
            max_iterations=MAX_ITERATIONS,
        )
    return run_dir


def run_case(case_id: str, root: Path, runtime: Path, python: str) -> dict[str, Any]:
    run_dir = prepare_case(case_id, root, runtime, python)
    state = core.load_state(run_dir)
    if state["status"] in {"success", "exhausted"}:
        return _json(run_dir / "report.json")
    if state["status"] not in {"awaiting-selector", "awaiting-measurement"}:
        raise StrictWanError(f"refusing to resume ambiguous case state: {state['status']}")

    strict = _strict_state(run_dir)
    if (
        state["status"] == "awaiting-selector"
        and state["attempts"]
        and state["attempts"][-1]["measurement_runs"]
        and strict["agent_2_turns"] < len(state["attempts"])
    ):
        _score_last_attempt(run_dir, strict)
    pending_candidate = _recover_pending_candidate(run_dir, strict)
    while True:
        state = core.load_state(run_dir)
        if state["status"] == "awaiting-measurement":
            feedback, _ = wan_suite.measure_case(root, case_id, timeout=240.0)
            if feedback["status"] == "measurement-error":
                raise StrictWanError(f"measurement infrastructure failed for {case_id}")
            _, success = _score_last_attempt(run_dir, strict)
            if success:
                return _json(run_dir / "report.json")
            if core.load_state(run_dir)["status"] == "exhausted":
                return _json(run_dir / "report.json")
            continue
        iteration = state["next_iteration"]
        if pending_candidate is not None:
            candidate = pending_candidate
            pending_candidate = None
        else:
            if strict["agent_1_thread"] is None:
                selector_prompt = _selector_initial_prompt(case_id, run_dir / "selector" / "workspace")
            else:
                previous = strict.get("last_agent_1_feedback_percent")
                if not isinstance(previous, (int, float)):
                    raise StrictWanError("Agent 1 may receive only a numeric irregularity")
                selector_prompt = _selector_retry_prompt(iteration, float(previous))
            strict["agent_1_turns"] += 1
            thread, candidate = _agent_turn(
                case_id=case_id,
                role="agent-1",
                prompt=selector_prompt,
                schema=CANDIDATE_SCHEMA,
                turn=strict["agent_1_turns"],
                thread_id=strict["agent_1_thread"],
                log_root=run_dir / "agents" / "agent-1",
            )
            strict["agent_1_thread"] = thread
            _save_strict(run_dir, strict)
        rejected = 0
        while True:
            try:
                _apply_candidate(run_dir, candidate, iteration)
                break
            except StrictWanError as exc:
                rejected += 1
                if rejected > 5:
                    raise StrictWanError(
                        f"Agent 1 exceeded the candidate-validation retry limit for {case_id}"
                    ) from exc
                strict["agent_1_turns"] += 1
                thread, candidate = _agent_turn(
                    case_id=case_id,
                    role="agent-1",
                    prompt=_selector_rejection_prompt(iteration, str(exc)),
                    schema=CANDIDATE_SCHEMA,
                    turn=strict["agent_1_turns"],
                    thread_id=strict["agent_1_thread"],
                    log_root=run_dir / "agents" / "agent-1",
                )
                strict["agent_1_thread"] = thread
                _save_strict(run_dir, strict)
        wan_suite.submit_case(root, case_id)
        feedback, assessment = wan_suite.measure_case(root, case_id, timeout=240.0)
        if feedback["status"] == "measurement-error":
            raise StrictWanError(f"measurement infrastructure failed for {case_id}")
        _, success = _score_last_attempt(run_dir, strict)
        if success:
            return _json(run_dir / "report.json")
        if feedback["status"] == "exhausted":
            return _json(run_dir / "report.json")
        if feedback["status"] not in {"retry", "invalid"}:
            raise StrictWanError(f"unexpected terminal status: {feedback['status']}")


def run_all(root: Path, runtime: Path, python: str) -> dict[str, Any]:
    results = []
    for case_id in wan.list_wan_cases():
        results.append(run_case(case_id, root, runtime, python))
    report = wan_report.write_reports(root, root)
    (root / "full-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (root / "full-report.md").write_text(wan_report.render_markdown(report))
    (root / "full-report.csv").write_text(wan_report.render_csv(report))
    return {"cases": len(results), "status": "complete"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    one = sub.add_parser("run-case")
    one.add_argument("case")
    all_cases = sub.add_parser("run-all")
    for command in (one, all_cases):
        command.add_argument("--root", type=Path, default=DEFAULT_ROOT)
        command.add_argument("--runtime-template", type=Path, required=True)
        command.add_argument("--python", required=True)
    args = parser.parse_args()
    try:
        if args.action == "run-case":
            value = run_case(args.case, args.root, args.runtime_template, args.python)
        else:
            value = run_all(args.root, args.runtime_template, args.python)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except (
        StrictWanError,
        core.EvaluationError,
        wan.WanStageError,
        wan_suite.WanSuiteError,
        subprocess.SubprocessError,
        OSError,
        ValueError,
    ) as exc:
        print(f"strict-wan: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
