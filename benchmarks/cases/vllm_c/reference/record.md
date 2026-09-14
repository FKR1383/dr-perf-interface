### vLLM case C. The input batch under churn: what an arrival and a departure cost

Driver `examples/vllm_run_batch.py` forces replacement: 24 requests through
`max_num_seqs=8` with output lengths spread 4..40, so most steps see an
arrival or a departure. Markers from `examples/vllm_mark_batch.py`. Runs
`out/vllm_batch` (82 steps, 25 admissions, 23 removals) and `out/vllm_batch_long`
(86-326-token prompts).

```
update_states     cost(num_reqs, num_new, num_finished) = 1,048.2*num_reqs + 45,598.9*num_new + 22,118.6*num_finished + 95,570.1   49.9% irregular
add_request       cost(num_prompt, num_blocks) = 275.2*num_prompt + 0*num_blocks + 46,456.8                                      2.8%
    per-prompt-token: PyArray_DiscoverDTypeAndShape_Recursive 85, PyArray_Pack 69, INT_setitem 58, PyLong_AsLong 22
condense          cost(num_reqs, empty) = 9.6*num_reqs + 12,163*empty + 11,258.2                                                45.1%
refresh_metadata  cost(num_reqs, num_added, num_moved) = 0*num_reqs + 3,420.9*num_added + 4,894.5*num_moved + 32,234.9           36.3%
remove_request    cost(num_reqs) = 37.8*num_reqs + 14,897   [num_reqs >= 4]                                                        0.0%
bt_commit         cost(num_reqs) = 0*num_reqs + 22,005.3                                                                          0.0%
```

**An arrival costs per prompt token, for a copy.** `InputBatch.add_request`
is 275-333 instructions per prompt token at under 3% unexplained, and the
attribution is numpy's scalar path: `PyArray_Pack`, `INT_setitem`,
`PyLong_AsLong`. That is `token_ids_cpu[req_index, :n] = request.prompt_token_ids`
and its two siblings at `gpu_input_batch.py:376/382/387`, a Python list
assigned element by element into an int32 row. A 2k-token prompt is about
615k instructions to admit, more than a whole steady step of the runner.

**A departure costs per row moved, not per token.** `condense` is 2.4k with
nothing to move and 54k-80k per row moved (12,163 per `empty` in the fit,
the rest in its 45% residue). The long run, with rows of 326 tokens instead
of 86, changed nothing: the cost is about 17 separate numpy row assignments
plus `block_table.move_row` (`gpu_input_batch.py:765-786`), each a full
dispatch, not the bytes copied. Then `refresh_metadata` rebuilds all sampling
metadata on any change, 10k when nothing changed and 79k-128k when something
did (`:846/858`). With 64 requests and continuous replacement: ~16k to
remove, ~54k to condense, ~73k to rebuild metadata, per finish, every step
one finishes.

**Third beat, measured** (`patches/vllm_input_batch.patch`, `out/vllm_batch_fix`,
`out/vllm_batch_long_fix`; text and token ids identical for all 24 requests
on both variants, plus a 150-trial differential test of the batch's thirteen
arrays, block tables and sampling metadata against the pristine module):

```
add_request        275.2*num_prompt + 46,457    ->   202.9*num_prompt + 42,629       (long prompts: 332.7 -> 269.6)
refresh_metadata   at the steady replace (8 requests, 1 added): 83,361 -> 44,595 per call   (-46.5%)
condense           per moved row, bursts of >= 3: 47,366 -> 33,844   (-28.5%); single departures unchanged
update_states      1,048.2*num_reqs + 45,598.9*num_new + 22,118.6*num_finished + 95,570  ->  856.2*num_reqs + 43,314.2*num_new + 19,919.1*num_finished + 94,570
```

The arrival copy is the instructive one. Ten candidates were measured under
drperf before choosing (`out/rowfill*`): `np.asarray` 334 per element,
`np.array(dtype=int32)` 334, `torch.tensor` 830, `np.fromiter` 269,
`array("i")` + `frombuffer` 271, every one with a larger constant than the
status quo's 333 + 3.6k. What won on both slope and constant is a cached
`memoryview` of each row assigned from `array("i", ids)`: 271 per element,
3,188 constant. The obvious rewrite would have been a regression, and the
ids arrive as a Python list everywhere upstream, so a cached array would
move the 270 rather than remove it. `refresh_metadata` is memoised on the
tuple of scalars it depends on, since every field is a scalar, a view into
storage that never moves, or a container mutated in place. `condense`
gathers `(src, dst)` pairs and applies each scalar array's moves in one
fancy-index assignment (destinations are always below sources, so nothing
overlaps); the measured crossover is 2.7 rows, so it batches at three.

Per arrival at 64 requests with 2k-token prompts about 168k fewer
instructions (131k in `add_request`, 36.5k in the metadata rebuild); per
burst of eight departures about 72k. Smaller than the surprise suggested,
and the formulas said why before the change: the per-token cost is a
conversion that has no cheaper form for a Python list, and the per-row cost
is dispatch count, which batching can only amortise.

**The steady step is not steady either.** At `num_new = num_finished = 0`
the trace means give `5,714*num_reqs + 79,617` for `update_states` while the
fit says 1,048 per request; the rest sits in the residue, and the attribution
names it: `PyFrozenSet_New`, `_PyDict_Next`, `PySet_Discard`, the set
arithmetic `cached_req_ids - (scheduled_req_ids - resumed_req_ids)` at
`gpu_model_runner.py:1287-1301` and the every-request loop at `:1404`, run
whether or not anything changed. Together with case A's `prepare_inputs`
constant, about a million instructions per step at 64 requests that do not
depend on the tokens being generated, single-threaded, while the OpenMP
workers (excluded from these counts, 0.3M-6.2M of spinning per call) wait.

**Relations** (`out/vllm_batch/learn.txt`, exact at all 82 steps):

```
update_states.num_new       = last(execute_model.num_reqs) - last(schedule.running)
update_states.num_finished  = last(bt_commit.num_reqs) - last(schedule.running)
refresh_metadata.num_added  = last(update_states.num_new)
schedule.waiting            = cum(generate_loop.unfinished) - count(add_request)
schedule.running            = count(add_request) + last(engine_step.unfinished) - cum(generate_loop.unfinished)
```

The scheduler's admission count sets, one for one, how many `add_request`,
`condense` and metadata rebuilds the runner pays, so an admission policy
that admits more per step is priced by these formulas before it is written.

---

