"""Mark the per-step token estimate in a copy of kimi_cli."""
import pathlib, sys
ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "kimi-mark/kimi_cli")

def edit(rel, subs, add_import=True):
    p = ROOT / rel
    s = p.read_text()
    for old, new in subs:
        if new in s: continue
        assert s.count(old) == 1, f"{rel}: anchor count {s.count(old)}"
        s = s.replace(old, new)
    if add_import and "import perfmark" not in s:
        lines = s.split("\n"); i = 1 if lines and lines[0].startswith("from __future__") else 0
        lines.insert(i, "import perfmark"); s = "\n".join(lines)
    p.write_text(s); print("marked", rel)

edit("llm.py", [(
"""    return (
        _estimate_text_tokens(system_prompt)
        + sum(_estimate_tool_tokens(tool) for tool in tools)
        + sum(_estimate_message_tokens(message) for message in history)
    )""",
"""    _n_msgs = len(history)
    _n_chars = sum(
        len(p.text) for m in history for p in m.content if isinstance(p, TextPart)
    )
    _n_tools = len(tools)
    with perfmark.region(
        "estimate_request_tokens", n_msgs=_n_msgs, n_chars=_n_chars, n_tools=_n_tools
    ):
        with perfmark.region("est_system", tag=1):
            _sys = _estimate_text_tokens(system_prompt)
        with perfmark.region("est_tools", n_tools=_n_tools):
            _tls = sum(_estimate_tool_tokens(tool) for tool in tools)
        with perfmark.region("est_history", n_msgs=_n_msgs, n_chars=_n_chars):
            _hst = sum(_estimate_message_tokens(message) for message in history)
        return _sys + _tls + _hst"""),
])
print("done")

# --- the whole per-step path
edit("soul/kimisoul.py", [
("""    async def _step(self) -> StepOutcome | None:
        \"\"\"Run a single step and return a stop outcome, or None to continue.""",
 """    async def _step(self) -> StepOutcome | None:  # noqa: D401
        \"\"\"Run a single step and return a stop outcome, or None to continue."""),
("""        assert self._runtime.llm is not None
        chat_provider = self._runtime.llm.chat_provider

        # ═══════════════════════════════════════════════════════════════════════
        # 2e.1. NOTIFICATION DELIVERY (root role only)""",
 """        assert self._runtime.llm is not None
        chat_provider = self._runtime.llm.chat_provider
        _pm_hist = self._context.history
        _pm_nmsgs = len(_pm_hist)
        _pm_nchars = sum(
            len(p.text) for m in _pm_hist for p in m.content if isinstance(p, TextPart)
        )
        _pm_step = perfmark.region(
            "agent_step", n_msgs=_pm_nmsgs, n_chars=_pm_nchars,
            n_tools=len(self._agent.toolset.tools),
        )
        _pm_step.__enter__()

        # ═══════════════════════════════════════════════════════════════════════
        # 2e.1. NOTIFICATION DELIVERY (root role only)"""),
("""        injections = await self._collect_injections()
        if injections:""",
 """        with perfmark.region("step_injections", n_msgs=_pm_nmsgs, n_chars=_pm_nchars):
            injections = await self._collect_injections()
        if injections:"""),
("""        effective_history = normalize_history(self._context.history)
        generation_overrides = self._compute_completion_overrides(""",
 """        with perfmark.region("step_normalize", n_msgs=_pm_nmsgs, n_chars=_pm_nchars):
            effective_history = normalize_history(self._context.history)
        generation_overrides = self._compute_completion_overrides("""),
])

edit("soul/kimisoul.py", [
("""        t0 = time.monotonic()
        try:
            result = await _kosong_step_with_retry()""",
 """        t0 = time.monotonic()
        _pm_llm = perfmark.region("step_llm_call", n_msgs=_pm_nmsgs, n_chars=_pm_nchars)
        _pm_llm.__enter__()
        try:
            result = await _kosong_step_with_retry()"""),
("""        plan_mode_before_tools = self._plan_mode
        results = await result.tool_results()""",
 """        _pm_llm.__exit__(None, None, None)
        plan_mode_before_tools = self._plan_mode
        with perfmark.region("step_tools", n_msgs=_pm_nmsgs, n_chars=_pm_nchars):
            results = await result.tool_results()"""),
("""        await asyncio.shield(self._grow_context(result, results))""",
 """        with perfmark.region("step_grow_context", n_msgs=_pm_nmsgs, n_chars=_pm_nchars):
            await asyncio.shield(self._grow_context(result, results))
        _pm_step.__exit__(None, None, None)"""),
])
