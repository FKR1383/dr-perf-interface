"""Insert perfmark regions into the copied kimi_cli tree (idempotent, anchored edits)."""
import io, re, sys, pathlib
ROOT = pathlib.Path("kimi-mark/kimi_cli")

def edit(rel, subs, add_import=True):
    p = ROOT / rel
    s = p.read_text()
    for old, new in subs:
        if new in s:
            continue
        assert s.count(old) == 1, f"{rel}: anchor {old[:60]!r} count={s.count(old)}"
        s = s.replace(old, new)
    if add_import and "import perfmark" not in s:
        lines = s.split("\n")
        i = 0
        if lines and lines[0].startswith("from __future__"):
            i = 1
        lines.insert(i, "import perfmark")
        s = "\n".join(lines)
    p.write_text(s)
    print("marked", rel)

# --- __main__.py: the boot import and the whole run
edit("__main__.py", [(
"""    from kimi_cli.cli import cli
    from kimi_cli.utils.environment import GitBashNotFoundError

    try:
        return cli(args=args, prog_name=_prog_name())""",
"""    with perfmark.region("boot_import", tag=1):
        from kimi_cli.cli import cli
        from kimi_cli.utils.environment import GitBashNotFoundError

    try:
        with perfmark.region("cli_run", tag=2):
            return cli(args=args, prog_name=_prog_name())"""),
])

# --- app.py: the create phases
edit("app.py", [
("""        _phase_t = time.monotonic()
        config = config if isinstance(config, Config) else load_config(config)
        _phase_timings_ms["config_ms"] = int((time.monotonic() - _phase_t) * 1000)""",
 """        _phase_t = time.monotonic()
        with perfmark.region("config_load", tag=3):
            config = config if isinstance(config, Config) else load_config(config)
        _phase_timings_ms["config_ms"] = int((time.monotonic() - _phase_t) * 1000)"""),
("""        runtime = await Runtime.create(
            config,
            oauth,
            llm,
            session,
            yolo,
            afk=afk,
            runtime_afk=runtime_afk,
            skills_dirs=skills_dirs,
        )""",
 """        with perfmark.region("runtime_create", tag=4):
            runtime = await Runtime.create(
                config,
                oauth,
                llm,
                session,
                yolo,
                afk=afk,
                runtime_afk=runtime_afk,
                skills_dirs=skills_dirs,
            )"""),
("""        _phase_t = time.monotonic()
        agent = await load_agent(
            agent_file,
            runtime,
            mcp_configs=mcp_configs or [],
            start_mcp_loading=not defer_mcp_loading,
        )""",
 """        _phase_t = time.monotonic()
        with perfmark.region("load_agent", tag=5):
            agent = await load_agent(
                agent_file,
                runtime,
                mcp_configs=mcp_configs or [],
                start_mcp_loading=not defer_mcp_loading,
            )"""),
])

# --- soul/agent.py: spec load, toolset load, plugin tools
edit("soul/agent.py", [
("""    agent_spec = load_agent_spec(agent_file)

    system_prompt = _load_system_prompt(""",
 """    with perfmark.region("load_spec", tag=6):
        agent_spec = load_agent_spec(agent_file)

    system_prompt = _load_system_prompt("""),
("""    toolset.load_tools(tools, tool_deps)""",
 """    toolset.load_tools(tools, tool_deps)  # region inside load_tools"""),
("""    plugin_tools = load_plugin_tools(get_plugins_dir(), runtime.config, approval=runtime.approval)""",
 """    with perfmark.region("plugin_tools", tag=7):
        plugin_tools = load_plugin_tools(get_plugins_dir(), runtime.config, approval=runtime.approval)"""),
])

# --- soul/toolset.py: the per-tool loop
edit("soul/toolset.py", [
("""        good_tools: list[str] = []
        bad_tools: list[str] = []

        for tool_path in tool_paths:
            try:
                tool = self._load_tool(tool_path, dependencies)""",
 """        good_tools: list[str] = []
        bad_tools: list[str] = []

        _n_tools = len(tool_paths)
        # Size of the transitive import closure of the selected tool modules: a
        # static property of the tool list, tabulated once (startup/closure.json).
        _n_mods = int(__import__("os").environ.get("KIMI_PM_NMODS", "0"))
        _pm_load = perfmark.region("load_tools", n_tools=_n_tools, n_mods=_n_mods)
        _pm_load.__enter__()
        for _tool_i, tool_path in enumerate(tool_paths):
            try:
                import sys as _sys
                _mods0 = len(_sys.modules)
                with perfmark.region("load_one_tool", idx=_tool_i, mods_before=_mods0):
                    tool = self._load_tool(tool_path, dependencies)"""),
("""        logger.info("Loaded tools: {good_tools}", good_tools=good_tools)
        if bad_tools:""",
 """        _pm_load.__exit__(None, None, None)
        logger.info("Loaded tools: {good_tools}", good_tools=good_tools)
        if bad_tools:"""),
])
print("done")

# --- second pass: split the remainder of cli_run
edit("cli/__init__.py", [
("""            if session_id is not None:
                session = await Session.find(work_dir, session_id)""",
 """            _pm_sess = perfmark.region("session_prep", tag=8); _pm_sess.__enter__()
            if session_id is not None:
                session = await Session.find(work_dir, session_id)"""),
("""            nonlocal _latest_created_session
            _latest_created_session = session""",
 """            _pm_sess.__exit__(None, None, None)
            nonlocal _latest_created_session
            _latest_created_session = session"""),
("""            instance = await KimiCLI.create(""",
 """            _pm_app = perfmark.region("app_create", tag=9); _pm_app.__enter__()
            instance = await KimiCLI.create("""),
("""            )
            startup_progress.stop()""",
 """            )
            _pm_app.__exit__(None, None, None)
            startup_progress.stop()"""),
])

# --- third pass: the deferred import block inside the click command body
edit("cli/__init__.py", [
("""    from kaos.path import KaosPath

    from kimi_cli.agentspec import DEFAULT_AGENT_FILE, OKABE_AGENT_FILE
    from kimi_cli.app import KimiCLI, enable_logging""",
 """    _pm_imp = perfmark.region("deferred_import", tag=10); _pm_imp.__enter__()
    from kaos.path import KaosPath

    from kimi_cli.agentspec import DEFAULT_AGENT_FILE, OKABE_AGENT_FILE
    from kimi_cli.app import KimiCLI, enable_logging"""),
("""    from kimi_cli.utils.logging import logger, open_original_stderr, redirect_stderr_to_logger""",
 """    from kimi_cli.utils.logging import logger, open_original_stderr, redirect_stderr_to_logger
    _pm_imp.__exit__(None, None, None)"""),
])
