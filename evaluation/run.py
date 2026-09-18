#!/usr/bin/env python3
"""Compare static variable discovery with an independent Dr. Perf experiment."""
import argparse
import json
import math
from pathlib import Path
import shlex
import shutil
from string import Template
import sys
import tempfile

try:
    from . import baseline_measure, codex_runner, drperf_measure
    from .measurement_session import MeasurementSession, rebase_command
    from .workload import FrozenWorkload
    from .results import MAX_ATTEMPTS, EvaluationError, best_attempt, comparison, summary, variables, write_json
except ImportError:
    import codex_runner
    import drperf_measure
    import baseline_measure
    from measurement_session import MeasurementSession, rebase_command
    from workload import FrozenWorkload
    from results import MAX_ATTEMPTS, EvaluationError, best_attempt, comparison, summary, variables, write_json

HERE = Path(__file__).resolve().parent


def search(executable, workspace, control, prompt, config, model=None):
    """Search to target or budget and select the lowest verified irregularity."""
    previous = []
    continuations = stalled = 0
    current_prompt = prompt
    threshold = config["target_irregularity"]
    while True:
        turn_control = control if not continuations else control / f"continuation-{continuations:03d}"
        answer = codex_runner.invoke(executable, "agent_drperf", workspace, turn_control,
                                     current_prompt, config["max_attempts"], model,
                                     Path(config["journal"]))
        recorded = drperf_measure.recorded_attempts(config)
        if answer["attempts"] != recorded:
            raise EvaluationError("Agent + Dr. Perf output does not match all recorded measurements")
        if recorded[:len(previous)] != previous:
            raise EvaluationError("a continuation changed earlier measurement records")
        best = best_attempt(recorded)
        if best is not None:
            # The measured score, not the agent's preference or attempt order,
            # determines the final selection.
            answer = {**answer, "selected_variables": best["variables"],
                      "final_formula": best["formula"], "final_irregularity": best["irregularity"]}
        selected = next(a for a in recorded if
                        a["variables"] == answer["selected_variables"] and
                        a["formula"] == answer["final_formula"] and
                        a["irregularity"] == answer["final_irregularity"])
        achieved = best is not None and best["irregularity"] < threshold
        stalled = stalled + 1 if len(recorded) == len(previous) else 0
        metadata = {"policy": "minimum_irregularity", "target_irregularity": threshold,
                    "target_met": achieved, "attempts_used": len(recorded),
                    "max_attempts": config["max_attempts"], "continuations": continuations,
                    "selected_attempt": selected["attempt"],
                    "best_attempt": best["attempt"] if best is not None else None}
        if achieved:
            return answer, {**metadata, "stop_reason": "target_met"}
        if len(recorded) >= config["max_attempts"]:
            return answer, {**metadata, "stop_reason": "attempt_limit_reached"}
        # An agent that repeatedly returns without measuring has failed to
        # follow the search contract. Bound retries and report the interruption.
        if stalled >= 2:
            return answer, {**metadata, "stop_reason": "agent_stopped_without_progress"}
        remaining = config["max_attempts"] - len(recorded)
        print(f"Agent + Dr. Perf has not reached <{threshold * 100:g}%; "
              f"continuing with {remaining} experiments remaining...", file=sys.stderr, flush=True)
        previous = recorded
        continuations += 1
        current_prompt = (prompt + "\n\nContinue in the same disposable workspace. "
                          "The target is unmet and measurement budget remains. "
                          f"There are {remaining} experiments remaining; the next attempt is "
                          f"{len(recorded) + 1}. Keep the journal and its numbering unchanged. "
                          "Use source inspection and measured feedback to test further candidates. "
                          "Stop when any successful attempt is strictly below the target or the "
                          "budget is exhausted. Select the lowest irregularity across all attempts. "
                          "Prior measurements and the best verified selection follow; "
                          "detailed evidence remains in the journal.\n" + json.dumps(answer, indent=2))


def copy_workspace(source, destination, results_dir):
    def ignore(directory, names):
        return [n for n in names if n in {".git", ".codex", ".eval-tmp", "__pycache__"}
                or Path(directory, n).resolve() in {results_dir, HERE / "results"}]

    # Copy untracked/dirty sources and build products too. Dereference symlinks:
    # retaining a symlink could direct instrumentation writes into the original.
    shutil.copytree(source, destination, ignore=ignore, symlinks=False)


def capture_files(base, prefix, captured):
    for path in base.rglob("*"):
        if path.is_file() and "codex-home" not in path.relative_to(base).parts:
            captured[f"{prefix}/{path.relative_to(base)}"] = path.read_bytes()


def agent_only_search(executable, snapshot, source, region, command, captured, model=None,
                      max_rounds=baseline_measure.DEFAULT_ROUNDS, measurement_session=None):
    """Static proposals alternate with isolated measurability checks, not fit feedback."""
    initial = None
    history = []
    prompt = Template((HERE / "prompts/agent_only.md").read_text()).substitute(region=repr(region))
    for number in range(1, max_rounds + 1):
        current_prompt = prompt
        if history:
            # history contains only prior proposals and allowlisted feasibility
            # advice, never formulas, scores, counts, traces, or other-agent output.
            current_prompt += (
                "\n\nRevise your previous answer using the measurability feedback below. "
                "You may use this feedback in addition to static source reasoning. "
                "It comes from a separate instrumentation service and concerns only "
                "whether your features can be represented and measured. It provides no "
                "evidence about how well they explain cost. You still MUST NOT run the "
                "application, Dr. Perf, or any experiments, edit files, or inspect other "
                "sessions/artifacts. Choose any revisions yourself from the source. "
                "Define scalar entry-state expressions precisely; do not replace array "
                "contents with their addresses, invent future values, replay the region, "
                "or change the workload or region. Return the same variable-only schema. "
                "If you cannot improve the answer under these restrictions, retain your "
                "best static answer; the bounded loop may end without a measurable set.\n" +
                json.dumps(history, indent=2))
        label = f"round-{number:03d}"
        print(f"Running Agent Only (measurability round {number}/{max_rounds})...",
              file=sys.stderr, flush=True)
        with tempfile.TemporaryDirectory(prefix="drperf-static-") as session:
            session = Path(session)
            target, control = session / "workspace", session / "control"
            shutil.copytree(snapshot, target)
            try:
                answer = codex_runner.invoke(executable, "agent_only", target, control,
                                             current_prompt, model=model)
            finally:
                capture_files(control, f"logs/agent_only/{label}", captured)
        if initial is None:
            initial = {"variables": list(answer["variables"])}
        print(f"Checking Agent Only measurability ({number}/{max_rounds})...",
              file=sys.stderr, flush=True)
        with tempfile.TemporaryDirectory(prefix="drperf-baseline-") as session:
            session = Path(session)
            target = session / "workspace"
            shutil.copytree(snapshot, target)
            control, journal = session / "control", session / "measurement"
            try:
                measured = baseline_measure.measure(
                    executable, target, control, journal, region,
                    rebase_command(command, source, target), answer["variables"], model,
                    **({"measurement_session": measurement_session} if measurement_session is not None else {}))
            finally:
                capture_files(control, f"logs/agent_only_instrumentation/{label}", captured)
                capture_files(journal, f"measurements/agent_only/{label}", captured)
        history.append({"round": number, "variables": list(answer["variables"]),
                        "feedback": baseline_measure.feedback(measured)})
        print(f"Agent Only measurability round {number}: {measured['status']}",
              file=sys.stderr, flush=True)
        if measured["status"] == "ok":
            stop_reason = "measurable"
            break  # Never retry because irregularity is high.
        if not baseline_measure.retryable(measured):
            stop_reason = "measurement_unavailable"
            break
    else:
        stop_reason = "round_limit_reached"
    return {"agent_only": answer, "agent_only_initial": initial,
            "agent_only_measurement": measured,
            "agent_only_measurability": {
                "method": "static_with_measurability_feedback", "rounds": history,
                "rounds_used": len(history), "max_rounds": max_rounds,
                "measurable": measured["status"] == "ok", "stop_reason": stop_reason}}


def evaluate(workspace, region, command, results_dir, max_attempts=MAX_ATTEMPTS, model=None,
             ground_truth=None, target_irregularity=0.1,
             agent_only_max_rounds=baseline_measure.DEFAULT_ROUNDS):
    if not 1 <= max_attempts <= MAX_ATTEMPTS:
        raise EvaluationError(f"max-attempts must be between 1 and {MAX_ATTEMPTS}")
    if not math.isfinite(target_irregularity) or not 0 < target_irregularity <= 1:
        raise EvaluationError("target irregularity must be a fraction greater than 0 and at most 1")
    if not 1 <= agent_only_max_rounds <= baseline_measure.MAX_ROUNDS:
        raise EvaluationError(f"agent-only-max-rounds must be between 1 and {baseline_measure.MAX_ROUNDS}")
    executable = codex_runner.find_codex()
    drperf_measure.check_build()
    captured = {}
    result = None
    try:
        # There are never two live competitor sessions or on-disk results.
        # Both copies come from one snapshot, including the user's local edits.
        with tempfile.TemporaryDirectory(prefix="drperf-evaluation-") as temp:
            root = Path(temp)
            if workspace == root or workspace in root.parents:
                raise EvaluationError("temporary directory is inside the workspace; set TMPDIR outside the workspace")
            snapshot = root / "snapshot"
            copy_workspace(workspace, snapshot, results_dir)
            workload = FrozenWorkload(snapshot, region)
            measurements = MeasurementSession(root / "measurement-runtime", workspace, workload, command)
            print(f"Frozen workload: {workload.origin} ({workload.metadata['sha256'][:12]})",
                  file=sys.stderr, flush=True)
            outputs = agent_only_search(executable, snapshot, workspace, region, command,
                                        captured, model, agent_only_max_rounds, measurements)
            with tempfile.TemporaryDirectory(prefix="drperf-competitor-") as session:
                session = Path(session)
                target = session / "workspace"
                shutil.copytree(snapshot, target)
                control = session / "control"
                journal = session / "measurements"
                journal.mkdir()
                config = {"workspace": str(target), "journal": str(journal),
                          "region": region, "command": rebase_command(command, workspace, target),
                          "measurement_service": True,
                          "max_attempts": max_attempts, "target_irregularity": target_irregularity}
                config_path = session / "measurement-config.json"
                write_json(config_path, config)
                prompt = Template((HERE / "prompts/drperf_agent.md").read_text()).substitute(
                    region=repr(region), command=shlex.join(config["command"]),
                    max_attempts=max_attempts, drperf_root=HERE.parent,
                    target_irregularity=target_irregularity, target_percent=f"{100 * target_irregularity:g}",
                    helper=shlex.join([sys.executable, str(HERE / "drperf_measure.py"),
                                       "--config", str(config_path)]))
                print("Running Agent + Dr. Perf...", file=sys.stderr, flush=True)
                try:
                    with measurements.serve(config):
                        answer, search_status = search(executable, target, control, prompt, config, model)
                    outputs["agent_drperf"] = answer
                finally:
                    # Hold logs in memory until BOTH competitors have ended.
                    capture_files(control, "logs/agent_drperf", captured)
                    capture_files(journal, "measurements", captured)
            result = {"region": region, **outputs, "search": search_status,
                      "measurement_protocol": measurements.protocol}
            if ground_truth is not None:
                truth = variables(ground_truth)
                result["ground_truth"] = truth
                result["comparison"] = {
                    "agent_only": comparison(outputs["agent_only"]["variables"], truth),
                    "agent_drperf": comparison(outputs["agent_drperf"]["selected_variables"], truth)}
    finally:
        for name, data in captured.items():
            path = results_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if result is not None:
            for competitor in ("agent_only", "agent_only_initial", "agent_only_measurability", "agent_drperf"):
                write_json(results_dir / f"{competitor}.json", result[competitor])
            write_json(results_dir / "agent_only_measurement.json", result["agent_only_measurement"])
            write_json(results_dir / "result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, usage="%(prog)s --workspace PATH --region NAME [options] -- COMMAND [ARGS...]")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS,
                        help=f"measurement budget, from 1 to {MAX_ATTEMPTS} (default: {MAX_ATTEMPTS})")
    parser.add_argument("--target-irregularity", type=float, default=0.1,
                        help="stop below this fraction (default: 0.10, meaning strictly below 10%%)")
    parser.add_argument("--ground-truth", help="comma-separated source expressions; an empty string means the empty set")
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--model", help="Codex model (default: your normal Codex configuration)")
    parser.add_argument("--agent-only-max-rounds", type=int, default=baseline_measure.DEFAULT_ROUNDS,
                        help="maximum static proposal/measurability rounds (default: 3, maximum: 10)")
    args_list = list(sys.argv[1:] if argv is None else argv)
    split = args_list.index("--") if "--" in args_list else len(args_list)
    args = parser.parse_args(args_list[:split])
    command = args_list[split + 1:]
    results_dir = None
    try:
        workspace = args.workspace.expanduser().resolve()
        if not workspace.is_dir():
            raise EvaluationError(f"target workspace does not exist: {workspace}")
        if not command:
            raise EvaluationError("missing workload command; put it after --")
        if not args.region.strip():
            raise EvaluationError("region must be nonempty")
        if not 1 <= args.max_attempts <= MAX_ATTEMPTS:
            raise EvaluationError(f"max-attempts must be between 1 and {MAX_ATTEMPTS}")
        if not math.isfinite(args.target_irregularity) or not 0 < args.target_irregularity <= 1:
            raise EvaluationError("target irregularity must be a fraction greater than 0 and at most 1")
        if not 1 <= args.agent_only_max_rounds <= baseline_measure.MAX_ROUNDS:
            raise EvaluationError(f"agent-only-max-rounds must be between 1 and {baseline_measure.MAX_ROUNDS}")
        truth = None if args.ground_truth is None else (
            variables([v.strip() for v in args.ground_truth.split(",")]) if args.ground_truth else [])
        if args.results_dir:
            results_dir = args.results_dir.expanduser().resolve()
            if results_dir == workspace or results_dir in workspace.parents:
                raise EvaluationError("results directory must not contain the target workspace")
            results_dir.mkdir(parents=True, exist_ok=True)
            if any(results_dir.iterdir()):
                raise EvaluationError("results directory must be empty")
        else:
            results_dir = Path(tempfile.mkdtemp(prefix="drperf-results-"))
        result = evaluate(workspace, args.region, command, results_dir, args.max_attempts,
                          args.model, truth, args.target_irregularity, args.agent_only_max_rounds)
        print(summary(result))
        print(f"\nResults: {results_dir / 'result.json'}")
        if result["agent_drperf"]["final_formula"] is None:
            raise EvaluationError("no model selected; see the recorded measurement statuses")
        if not result["search"]["target_met"]:
            print(f"evaluation: irregularity target not met ({result['search']['stop_reason']}); "
                  "selected model and evidence saved", file=sys.stderr)
            return 2
        return 0
    except (EvaluationError, OSError, shutil.Error) as exc:
        print(f"evaluation: {exc}", file=sys.stderr)
        if results_dir is not None:
            print(f"Artifacts: {results_dir}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
