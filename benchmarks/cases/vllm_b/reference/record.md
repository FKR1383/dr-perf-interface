### vLLM case B. Admitting a request: what a prompt costs before its first token

Eleven regions on the admission and teardown path (`examples/vllm_mark_req.py`),
driver `examples/vllm_run_req.py`: 16 prompts from 12 to 662 tokens, four
output tokens each so admission dominates, and a second `generate()` over the
same prompts to see what is cached. Runs `out/vllm_req` and `out/vllm_req_n`
(instrumented 36.9 s and 46.1 s with late attach).

```
render_prompt        cost(prompt_chars) = 2,089.7*prompt_chars + 281,254.6   [prompt_chars >= 270]   29.6% irregular
process_inputs       cost(num_tokens)   = 315.6*num_tokens + 372,902.8       [num_tokens >= 62]       4.3%
    per-token: PyObject_RichCompareBool 116, PyLong_AsSsize_t 74, PyList_Size 33, PyIter_Next 30
    constant:  _PyEval_EvalFrameDefault 132,612
engine_add_request   cost(num_tokens)   = 544.8*num_tokens + 603,204.4       [num_tokens >= 62]      12.0%
request_init         cost(num_prompt)   = 79.3*num_prompt + 23,844.1                                  58.6%
    irregular: _PyObject_GC_Resize 30,053
core_add_request     cost(num_tokens, num_prompt) = 0*num_tokens + 0*num_prompt + 40,717.4             5.9%
sched_free_request   cost(running, num_blocks, num_tokens) = 0*running + 1,988.3*num_blocks - 13.2*num_tokens + 41,142.4   13.0%
kv_free              cost(num_blocks, num_tokens) = 1,526.9*num_blocks - 8.5*num_tokens + 8,291.4       11.8%
```

**The tokenizer is the per-request cost and nothing caches it.** 2,090
instructions per prompt character, and the second pass over identical
prompts costs the same (9,233,195 then 9,173,733 for the 2,970-character
set). It is 51% of admission on the first pass and 82% on the second. A
2k-token prompt is about 19M instructions, paid again on every call.

**The per-token slope of `process_inputs` is a bounds check.** 315.6 per
token, attributed entirely to `RichCompareBool`, `PyLong_AsSsize_t`,
`PyIter_Next` and `PyList_Size`: that is `max(prompt_ids)` and
`min(prompt_ids)` at `vllm/v1/engine/input_processor.py:485-486`, two full
Python scans of a token list the tokenizer just produced. 646k per 2k-token
request, for nothing.

**373k instructions of fixed work per request, before any token is
touched.** All interpreter, dominated by `SamplingParams.clone()`, which is
`copy.deepcopy` (`vllm/sampling_params.py:769-772`, called from
`input_processor.py:329` with `skip_clone` defaulting to False), plus
validation; `core_add_request` and `sched_add_request` add 45k more, both
flat in everything. 27M instructions of object copying per 64 requests,
independent of prompt size.

**`Request.__init__` has a staircase the declared state cannot fit.** Per-point
means by prompt length: 34.5k at 12 tokens, 39.7k at 122, then 88.0k at
162, 118.1k at 302, 163.3k at 422, 208.2k at 542, 253.3k at 662. Flat within
each 128-token block, about 45k more per block. `num_prompt` fits 79 per
token and leaves 58.6% unexplained; the real driver is `num_prompt // 128`,
the block hashes computed at construction (`update_block_hashes()` at
`vllm/v1/request.py:211`) plus a full copy of the token list (`request.py:146`,
the `_PyObject_GC_Resize` in the residue). A caller reasoning in tokens
cannot see it; a caller who declares blocks gets a formula. 16 blocks of a
2k prompt: ~750k per request.

**The detokenizer decodes the whole prompt at admission.** `engine_add_request`
net of its nested regions is 145k + ~210 per prompt token:
`FastIncrementalDetokenizer.__init__` builds `DecodeStream(ids=prompt_token_ids)`
(`vllm/v1/engine/detokenizer.py:184`) to prime a stream that will only ever
emit the new tokens. ~430k per 2k-token request, discarded.

**The first request pays a disk scan.** The first `process_inputs` trigger
costs 48,027,055 instructions against 406,340 for the same prompt on the
second pass; the whole 99% irregular share of the small-prompt regime is
that one call. It is `_validate_logits_processors` loading plugins through
`importlib.metadata.entry_points()` (`vllm/v1/sample/logits_processor/__init__.py:57`),
reading 170 distributions' metadata, on the admission path rather than at
startup: first-request latency, not model load.

**Third beat, measured** (`patches/vllm_admission.patch`, `out/vllm_req_fix`;
all 32 generated texts and token id lists identical):

```
process_inputs       315.6*num_tokens + 372,902.8   ->   109.2*num_tokens + 386,776.3
engine_add_request   544.8*num_tokens + 603,204.4   ->   227.5*num_tokens + 618,328.6
```

Two changes. The bounds check becomes one C pass, `array("L", prompt_ids)`,
which proves every id is non-negative by succeeding and falls back to the
original two scans, with the original messages, if it does not; the
per-token attribution that read `RichCompareBool`, `PyLong_AsSsize_t`,
`PyList_Size`, `PyIter_Next` now reads `PyInit_array`, `PyLong_AsUnsignedLong`,
`PySequence_GetItem`. And the detokenizer primes its stream with the last
seven prompt tokens instead of all of them, the constant the slow path
already uses; for opt-125m's byte-level decoder this is provably
equivalent, and it was checked against all 50,265 vocabulary ids as the
first output token and 48k random sequences with zero mismatches. That
argument is decoder-specific, and a non-concatenative decoder would need a
guard. Per 2k-token prompt: about 409k fewer instructions in
`process_inputs` (-40%) and 635k in `engine_add_request` (-37%); break-even
at 67 tokens.

The tool also chose between candidates: measured under drperf,
`np.asarray(prompt_ids)` costs 332 per token, worse than the two scans it
would replace, and `all(map(...))` four times worse; only `array("L")` at
110 beat CPython's `max`/`min` at 156 per pass. A fix picked from
intuition would have been a regression.

**Third beat for the staircase, measured** (`patches/vllm_request_init.patch`,
`out/vllm_req_blocks`, `out/vllm_req_fix2`). First the fit: `num_blocks` is
not reachable from the constructor's arguments, so the hasher closure now
publishes its block size and the marker reads it. With that state declared:

```
request_init   cost(num_prompt, num_blocks) = -4.0*num_prompt + 43,273.3*num_blocks + 25,363.4     57.7% -> 12.7% irregular
    per block: _PyObject_GC_Resize 19,526, _PyEval_EvalFrameDefault 3,714, PyLong_AsLongAndOverflow 2,706, PyList_AsTuple 1,635, SHA1_Init 1,240
```

The 79 per token was the staircase seen through the wrong state; per block
it is 43k and per token it is nothing. Then the change: the prompt copy has
to stay (`_all_token_ids` is mutated by the session and connector paths),
but every reader of `block_hashes` runs from `Scheduler.schedule` or later,
so the hashes became a lazy attribute computed on first read. All 32 outputs,
all 54 block hashes and the prefix-cache hit counts are identical.

```
request_init         78.5*n + 23,998 (57.7%)     ->   -2.5*n + 1,086*blocks + 18,829 (34.1%)     662 tokens: 254,024 -> 29,128
engine_add_request   227.5*n + 618,329 (13.6%)   ->   136.8*n + 620,710 (7.0%)                   662 tokens: 1,011,290 -> 760,785
```

About 692k instructions per 2k-token prompt leave the admission path. They
do not leave the program: `schedule` at sixteen waiting rose from 2,655,476
to 3,523,500 per call, and the +2.46M there matches the -2.46M off admission
across the 32 requests exactly. This one moves work to where it is needed
and shortens time-to-first-schedule; it does not reduce total instructions,
and the formulas say so.

**Teardown is per block, and the running list is rebuilt per step.**
`_free_request` is 1,988 per block (of which `kv_free` 1,527) plus 41k, with
`running` at exactly 0: it does not scan the running list. The scan is
`self.running = remove_all(...)` at `scheduler.py:2035`, outside that
region, and surfaces as `update_from_output`'s 4,938 per running request.

**Relations** (`out/vllm_req/learn.txt`, `out/vllm_req_n/learn.txt`):

```
engine_step.unfinished = cum(add_requests_loop.num_prompts) - count(kv_free)
schedule.waiting       = cum(add_requests_loop.num_prompts) - cum(execute_model.num_reqs) + cum(schedule.running)
core_add_request.num_prompt = last(process_inputs.num_tokens) = last(engine_add_request.num_tokens) = last(request_init.num_prompt)
kv_free.num_blocks     = last(sched_free_request.num_blocks)
```

The first says the step loop's load is admitted minus freed, exactly; the
third says five regions bill the same prompt length, so their slopes add:
2,090 per character, then 316, 229 and 79 per token, then 45k per 128-token
block, all for one input.

---

