"""Drive one Kimi Code CLI cold start with a chosen number of tools.

Usage: run_kimi.py [n_tools=N] [n_subagents=N]
The agent spec is generated so the tool list has exactly n_tools entries;
KIMI_HOME is a fresh directory per run so no session or cache state carries over.
"""
import os, shutil, sys, tempfile, pathlib

ALL_TOOLS = [
    "kimi_cli.tools.agent:Agent",
    "kimi_cli.tools.ask_user:AskUserQuestion",
    "kimi_cli.tools.todo:SetTodoList",
    "kimi_cli.tools.shell:Shell",
    "kimi_cli.tools.background:TaskList",
    "kimi_cli.tools.background:TaskOutput",
    "kimi_cli.tools.background:TaskStop",
    "kimi_cli.tools.file:ReadFile",
    "kimi_cli.tools.file:ReadMediaFile",
    "kimi_cli.tools.file:Glob",
    "kimi_cli.tools.file:Grep",
    "kimi_cli.tools.file:WriteFile",
    "kimi_cli.tools.file:StrReplaceFile",
    "kimi_cli.tools.web:SearchWeb",
    "kimi_cli.tools.web:FetchURL",
    "kimi_cli.tools.plan:ExitPlanMode",
    "kimi_cli.tools.plan.enter:EnterPlanMode",
]

def main():
    args = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k] = int(v)
    n_tools = args.get("n_tools", len(ALL_TOOLS))
    n_subagents = args.get("n_subagents", 3)

    pkg = pathlib.Path(__file__).resolve().parent.parent / "kimi-mark" / "kimi_cli"
    agents = pkg / "agents" / "default"
    work = pathlib.Path(tempfile.mkdtemp(prefix="kimirun-"))
    home = work / "home"
    home.mkdir()
    os.environ["KIMI_HOME"] = str(home)
    os.environ["KIMI_DISABLE_TELEMETRY"] = "1"
    os.environ["NO_COLOR"] = "1"
    # Declared state for the load_tools region: the union import closure of the
    # chosen tool prefix, from the tabulation in startup/closure.json.
    import json
    tab = json.load(open(pathlib.Path(__file__).resolve().parent / "closure.json"))
    os.environ["KIMI_PM_NMODS"] = str(tab[n_tools - 1]["cum"] if n_tools else 0)

    subs = {"coder": "Good at general software engineering tasks.",
            "explore": "Fast codebase exploration with prompt-enforced read-only behavior.",
            "plan": "Read-only implementation planning and architecture design."}
    spec = ["version: 1", "agent:", '  name: ""',
            f"  system_prompt_path: {agents / 'system.md'}",
            "  system_prompt_args:", '    ROLE_ADDITIONAL: ""', "  tools:"]
    spec += [f'    - "{t}"' for t in ALL_TOOLS[:n_tools]]
    spec.append("  subagents:")
    for name, desc in list(subs.items())[:n_subagents]:
        spec += [f"    {name}:", f"      path: {agents / (name + '.yaml')}", f'      description: "{desc}"']
    agent_file = work / "agent.yaml"
    agent_file.write_text("\n".join(spec) + "\n")

    sys.argv = ["kimi", "--quiet", "-p", "hi", "--agent-file", str(agent_file),
                "--work-dir", str(work)]
    from kimi_cli.__main__ import main as kimi_main
    try:
        kimi_main()
    except SystemExit:
        pass
    finally:
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    main()
