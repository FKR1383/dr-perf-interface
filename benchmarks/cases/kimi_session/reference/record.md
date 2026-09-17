## The same CLI, running: a per-step cost function and a 21% faster session

The cold-start case above is honest about its own weakness. A startup is a
single event with no state to vary, the fit failed twice before the case
turned into a list of two names, and `python -X importtime` would have found
the same four imports. This section is the case that startup could not be:
a region whose cost is a *function* of something the caller varies, where
the surprise is a coefficient rather than a hot function, and where the same
formula, re-derived after the fix, is the verification.

**Driving a real agent loop with no model.** `startup/run_agent_kimi.py`
runs one user turn through the production path with provider type `kimi`
pointed at `startup/stub_llm.py`, an in-process HTTP server on localhost
that replays a fixed script of assistant messages. Every step calls a tool,
each on a different file, because the toolset deduplicates identical calls
and re-reading one path would not grow the conversation. So the session is a
real multi-step agent loop, entirely local, with the history growing by a
controlled amount per step.

The provider type matters. The first attempt used the built-in
`_scripted_echo` provider and measured nothing, because
`_compute_completion_overrides` returns early when the provider is not
Kimi-backed, and the region under study never ran. That is worth stating
plainly: a driver that does not enter the code path produces a clean,
confident zero.

**Beat one, the fit.** The region is `estimate_request_tokens`, which
`KimiSoul` calls once per step, before every model call, over the whole
conversation and every tool schema. Declared states: the number of messages,
the total characters of text in them, and the number of tools.

```
$ drperf run --blocks --repeat 2 --state n_msgs=8,24,40,56,64 \
      --state chars_per_msg=200,800,1600 --state n_tools=5,11,17 \
      -o out/tok_fit2 -- ./kimi-venv/bin/python startup/run_tokens.py steps=3

cost(n_msgs, n_chars, n_tools) = 7,894.7*n_msgs + 437.5*n_chars
                               + 270,272.8*n_tools + 1,967,904.9
    blocks: 2102 affine, 1237 constant, 34 irregular    (0.1% of cost)
```

**0.1% irregular**, three separated coefficients. Getting there took one
correction that drperf asked for: the first sweep held the tool count at
seventeen, and the tool said so rather than guessing, reporting that
`n_tools` was collinear with the other states and folding it into the
constant. Varying it separated the term.

**Beat two, the surprise: two coefficients that should not exist.**

- **437.5 instructions per character of conversation, per step.** Counting
  characters costs one Python loop iteration each, because
  `_estimate_text_tokens` is `sum(char.isascii() for char in text)`: a
  generator frame and an attribute call per character. The cost is per step
  and proportional to the whole history, so over a session it is quadratic.
- **270,272.8 instructions per tool, per step.** Each tool's schema is
  re-serialised with `json.dumps` and re-counted on every step, though the
  toolset hands back the same `Tool` objects for the life of the session.

Neither is visible as a hot function. A profiler reports time inside
`_estimate_text_tokens`; what it does not report is that the time is
proportional to conversation length and paid again on every step, which is
the part that decides whether to fix it and what the fix is worth.

**Beat three, the fix.** Two edits in `kimi_cli/llm.py`, plus a memo for the
per-step message conversion in `kosong/chat_provider/kimi.py`, where
`_convert_message` deep-copies every message in the history on every step.

```python
def _estimate_text_tokens(text: str) -> int:
    if text.isascii():                       # one C scan, the common case
        return (len(text) + 3) // 4
    ascii_count = len(text.encode("ascii", "ignore"))   # exact, still in C
    non_ascii_count = len(text) - ascii_count
    return (ascii_count + 3) // 4 + non_ascii_count
```

**The same formula, re-derived after the fix**, same command, same states:

| term | before | after | factor |
|---|---|---|---|
| per character of history | 437.5 | 0.371 | 1,179x |
| per tool | 270,272.8 | 16,101.2 | 16.8x |
| per message | 7,894.7 | 3,936.7 | 2.0x |
| constant | 1,967,904.9 | 77,810.9 | 25.3x |
| irregular | 0.1% | 1.3% | |

**Regions, over a 40-step session** (`out/tok_before`, `out/tok_after`):

| region | calls | before | after | change |
|---|---|---|---|---|
| `estimate_request_tokens` | 40 | 1,675,521,657 | 22,552,296 | -98.7% |
| of it, `est_history` | 40 | 792,062,423 | 11,771,864 | -98.5% |
| of it, `est_tools` | 40 | 605,830,263 | 2,604,227 | -99.6% |
| of it, `est_system` | 40 | 275,144,162 | 5,644,108 | -97.9% |
| `step_llm_call` | 40 | 6,126,634,942 | 5,670,573,716 | -7.4% |
| `step_injections` | 52 | 2,128,670,715 | 1,868,104,744 | -12.2% |
| `agent_step` | 40 | 8,085,458,030 | 5,978,360,180 | -26.1% |
| whole process | | 17,399,606,671 | 11,894,112,319 | -31.6% |

**End to end**, fresh processes, no instrumentation, best and median:

| session | stock 1.50.0 | all fixes | change |
|---|---|---|---|
| 60 steps, 8 KB per read (7 runs) | 5.509 / 5.620 s | 4.376 / 4.433 s | **-21.1%** |
| 120 steps, 8 KB per read (3 runs) | 10.945 / 11.053 s | 8.939 / 9.024 s | -18.4% |
| per-step fixes alone, 60 steps | 4.782 / 4.796 s | 4.357 / 4.377 s | -8.7% |

**Equivalence.** `startup/equiv_tokens.py` compares 473 estimates across
plain ASCII, ASCII control characters, Latin-1 accents, CJK, astral emoji,
every code point from 0 to 300 and a block of CJK one character at a time,
plus repeated whole-request estimates to exercise the caches: identical on
both trees. `startup/equiv_wire.py` captures every JSON body the CLI sends
to the stub endpoint across a ten-step session and compares them after
normalising the three fields that vary per run (the timestamp in the system
prompt, the session UUID, and the temp directory): the ten request bodies
are identical.

**What was left on the table, and why.** After these fixes the largest
remaining cost in a long session is the OpenAI SDK's own request transform,
about 45% of the profile, which walks the entire message payload through a
TypedDict-driven conversion on every request. It has exactly the same shape,
per step and proportional to history, and it is inherent to resending the
conversation each turn. Bypassing it means calling below the SDK's public
`create()`, which is version-fragile, so it is reported rather than fixed.

**Why this is the case the cold start was not.** Here the deliverable was a
number the code does not state anywhere: what one more character of
conversation costs on every subsequent step. The fit made that number
trustworthy at 0.1% irregular, the coefficient identified the fix, and
re-deriving the same formula afterwards showed the term collapse by three
orders of magnitude. That is a cost function doing work a profile cannot,
and this time the wall clock moved with it.

