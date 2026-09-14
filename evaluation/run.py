#!/usr/bin/env python3
"""Compare static variable discovery with an independent Dr. Perf experiment."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
from string import Template
import sys
import tempfile

try:
    from . import codex_runner, drperf_measure
    from .results import EvaluationError, comparison, summary, variables, write_json
except ImportError:
    import codex_runner
    import drperf_measure
    from results import EvaluationError, comparison, summary, variables, write_json

HERE = Path(__file__).resolve().parent


def copy_workspace(source, destination, results_dir):
    def ignore(directory, names):
        return [n for n in names if n in {".git", ".codex", ".eval-tmp", "__pycache__"}
                or Path(directory, n).resolve() in {results_dir, HERE / "results"}]

    # Copy untracked/dirty sources and build products too. Dereference symlinks:
    # retaining a symlink could direct instrumentation writes into the original.
    shutil.copytree(source, destination, ignore=ignore, symlinks=False)


def rebase_command(command, source, destination):
    def rebase(arg):
        if arg == str(source) or arg.startswith(str(source) + os.sep):
            return str(destination) + arg[len(str(source)):]
        if "=" in arg:
            key, value = arg.split("=", 1)
            if value == str(source) or value.startswith(str(source) + os.sep):
                return key + "=" + str(destination) + value[len(str(source)):]
        return arg

    return [rebase(arg) for arg in command]


def evaluate(workspace, region, command, results_dir, max_attempts=5, model=None,
             ground_truth=None):
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
            outputs = {}
            for competitor in ("agent_only", "agent_drperf"):
                with tempfile.TemporaryDirectory(prefix="drperf-competitor-") as session:
                    session = Path(session)
                    target = session / "workspace"
                    shutil.copytree(snapshot, target)
                    control = session / "control"
                    journal = session / "measurements"
                    journal.mkdir()
                    config = {"workspace": str(target), "journal": str(journal),
                              "region": region, "command": rebase_command(command, workspace, target),
                              "max_attempts": max_attempts}
                    config_path = session / "measurement-config.json"
                    # No experimental prompt/config exists during the static run.
                    if competitor == "agent_drperf":
                        write_json(config_path, config)
                    prompt_name = "agent_only" if competitor == "agent_only" else "drperf_agent"
                    prompt = Template((HERE / "prompts" / f"{prompt_name}.md").read_text()).substitute(
                        region=repr(region), command=shlex.join(config["command"]),
                        max_attempts=max_attempts, drperf_root=HERE.parent,
                        helper=shlex.join([sys.executable, str(HERE / "drperf_measure.py"),
                                           "--config", str(config_path)]))
                    print(f"Running {'Agent Only' if competitor == 'agent_only' else 'Agent + Dr. Perf'}...",
                          file=sys.stderr, flush=True)
                    try:
                        answer = codex_runner.invoke(executable, competitor, target, control, prompt,
                                                     max_attempts, model,
                                                     journal if competitor == "agent_drperf" else None)
                        if competitor == "agent_drperf":
                            recorded = drperf_measure.recorded_attempts(config)
                            if answer["attempts"] != recorded:
                                raise EvaluationError("Agent + Dr. Perf output does not match all recorded measurements")
                        outputs[competitor] = answer
                    finally:
                        # Hold logs in memory until BOTH sessions have ended.
                        # Raw measurement data is saved for audit/re-analysis.
                        for base, prefix in ((control, f"logs/{competitor}"),
                                             (journal, "measurements")):
                            for path in base.rglob("*"):
                                if path.is_file() and "codex-home" not in path.relative_to(base).parts:
                                    captured[f"{prefix}/{path.relative_to(base)}"] = path.read_bytes()
            result = {"region": region, **outputs}
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
            for competitor in ("agent_only", "agent_drperf"):
                write_json(results_dir / f"{competitor}.json", result[competitor])
            write_json(results_dir / "result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, usage="%(prog)s --workspace PATH --region NAME [options] -- COMMAND [ARGS...]")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--ground-truth", help="comma-separated source expressions; an empty string means the empty set")
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--model", help="Codex model (default: your normal Codex configuration)")
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
        if not args.region.strip() or args.max_attempts < 1:
            raise EvaluationError("region must be nonempty and max-attempts must be positive")
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
                          args.model, truth)
        print(summary(result))
        print(f"\nResults: {results_dir / 'result.json'}")
        if result["agent_drperf"]["final_formula"] is None:
            raise EvaluationError("no model selected; see the recorded measurement statuses")
        return 0
    except (EvaluationError, OSError, shutil.Error) as exc:
        print(f"evaluation: {exc}", file=sys.stderr)
        if results_dir is not None:
            print(f"Artifacts: {results_dir}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
