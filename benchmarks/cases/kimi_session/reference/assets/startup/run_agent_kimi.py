"""Drive a real multi-step Kimi agent session against a local stub endpoint.

Usage: run_agent_kimi.py [steps=N] [file_chars=N] [n_tools=N]

Uses provider type `kimi`, so the whole production per-step path runs, including
the request token estimate that only executes for Kimi-backed providers. The
endpoint is an in-process HTTP server on localhost, so no model and no external
network are involved.
"""
import json, os, pathlib, random, shutil, sys, tempfile

TOOLS = ["kimi_cli.tools.agent:Agent", "kimi_cli.tools.ask_user:AskUserQuestion",
         "kimi_cli.tools.todo:SetTodoList", "kimi_cli.tools.shell:Shell",
         "kimi_cli.tools.background:TaskList", "kimi_cli.tools.background:TaskOutput",
         "kimi_cli.tools.background:TaskStop", "kimi_cli.tools.file:ReadFile",
         "kimi_cli.tools.file:ReadMediaFile", "kimi_cli.tools.file:Glob",
         "kimi_cli.tools.file:Grep", "kimi_cli.tools.file:WriteFile",
         "kimi_cli.tools.file:StrReplaceFile", "kimi_cli.tools.web:SearchWeb",
         "kimi_cli.tools.web:FetchURL", "kimi_cli.tools.plan:ExitPlanMode",
         "kimi_cli.tools.plan.enter:EnterPlanMode"]


def main():
    args = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k] = int(v)
    steps = args.get("steps", 12)
    file_chars = args.get("file_chars", 4000)
    n_tools = args.get("n_tools", len(TOOLS))

    tree = os.environ.get("KIMI_TREE", "kimi-mark")
    root = pathlib.Path(__file__).resolve().parent.parent
    agents = root / tree / "kimi_cli" / "agents" / "default"
    work = pathlib.Path(tempfile.mkdtemp(prefix="kimikimi-"))
    home = work / "home"
    home.mkdir()
    os.environ["KIMI_HOME"] = str(home)
    os.environ["KIMI_DISABLE_TELEMETRY"] = "1"
    os.environ["NO_COLOR"] = "1"

    rng = random.Random(11)
    words = ("the quick brown fox reads a file and greps the repository for a symbol then "
             "writes the patch and runs the test suite again before reporting back").split()

    def text(n):
        out, total = [], 0
        while total < n:
            w = rng.choice(words)
            out.append(w)
            total += len(w) + 1
        return " ".join(out)[:n]

    # A distinct file per step: identical tool calls are deduplicated by the
    # toolset, so re-reading one path would not grow the conversation.
    turns = []
    for i in range(steps - 1):
        target = work / f"notes_{i}.txt"
        target.write_text(text(file_chars) + "\n")
        turns.append({"text": "reading notes %d" % i,
                      "tool_call": {"id": "call_%d" % i, "name": "ReadFile",
                                    "arguments": json.dumps({"path": str(target)})}})
    turns.append({"text": text(400), "tool_call": None})

    sys.path.insert(0, str(root / "startup"))
    import stub_llm
    base_url, shutdown = stub_llm.start(turns)

    cfg = {"default_model": "fake", "default_yolo": True, "telemetry": False,
           "loop_control": {"max_steps_per_turn": 400},
           "providers": {"local": {"type": "kimi", "base_url": base_url, "api_key": "stub"}},
           "models": {"fake": {"provider": "local", "model": "stub",
                               "max_context_size": 2000000}}}
    cfg_file = work / "config.json"
    cfg_file.write_text(json.dumps(cfg))

    spec = ["version: 1", "agent:", '  name: ""',
            f"  system_prompt_path: {agents / 'system.md'}",
            "  system_prompt_args:", '    ROLE_ADDITIONAL: ""', "  tools:"]
    spec += [f'    - "{t}"' for t in TOOLS[:n_tools]]
    spec += ["  subagents:", "    coder:", f"      path: {agents / 'coder.yaml'}",
             '      description: "Good at general software engineering tasks."']
    agent_file = work / "agent.yaml"
    agent_file.write_text("\n".join(spec) + "\n")

    sys.argv = ["kimi", "--quiet", "-p", "please look at the notes and summarise",
                "--agent-file", str(agent_file), "--config-file", str(cfg_file),
                "--work-dir", str(work), "--yolo"]
    from kimi_cli.__main__ import main as kimi_main
    try:
        kimi_main()
    except SystemExit:
        pass
    finally:
        shutdown()
        print(f"steps={steps} file_chars={file_chars} n_tools={n_tools}", file=sys.stderr)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
