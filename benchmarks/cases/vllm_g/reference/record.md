### vLLM case G. The scheduler under pressure: what waiting costs, what preemption costs, and a correction

Three workloads on a copy marked at the scheduler's queue and admission paths
(`examples/vllm_mark_sched.py`, `examples/vllm_run_sched.py`): saturation
(48 requests through `max_num_seqs=8`, up to 43 waiting, `out/vllm_sched_sat`),
priority scheduling under KV pressure (20 requests, 44 blocks of 16 tokens,
prefix caching off, 15 preemptions, `out/vllm_sched_prio`), and chunked
prefill (six 990-1,590-token prompts through a 128-token budget,
`out/vllm_sched_chunk`). A fourth run with finer sub-regions was discarded:
1,980 unmatched region ends, the late-attach race.

```
sat    schedule              cost(running, waiting) = 971.3*running + 0*waiting + 69,719.8                  94.1% irregular
       sched_waiting_eval    cost(num_tokens, num_computed, waiting) = 0 + 0 + 0 + 187,660.7               15.4%
       cached_request_data   cost(num_running, ...) = 4,852*num_running + 12,743.2                          1.8%
       fcfs_peek / fcfs_pop  2,572.6 / 441, flat in queue length                                             0.0%
prio   sched_preempt         cost(running, preempted, num_new_tokens) = 2,140.5*running + 0 + 0 + 94,086.3   14.9%
           per running: _PyTuple_Resize 358.6, PyTuple_GetSlice 210.6, PyObject_RichCompareBool 203.8, PyTuple_New 139.4
       prio_pop 76*queue_len + 3,057 | prio_prepend 32.3*queue_len + 19,746 | prio_peek 270
chunk  kv_allocate_slots     cost(num_new_tokens, num_computed, num_new_computed, num_tokens) = 8.4*num_new_tokens - 0.1*num_computed + 12.2*num_new_computed + 0 + 27,253.2   49.0%
```

**The correction.** Case B reported `schedule` at 55,206 and the baseline at
60,134 per waiting request per step. With 43 requests genuinely waiting the
coefficient is 0: `scheduler.py:762` breaks out before any per-waiting work
once `max_num_seqs` is reached, and `learn` shows `count(sched_waiting_eval)
= count(fcfs_peek) = count(fcfs_pop) = count(kv_get_computed_blocks)` = 49 in
139 steps, one probe per admission and none otherwise. The earlier
coefficient was admission cost aliased onto a `waiting` state that moved in
step with admissions in those runs. Two hundred waiting requests cost the
scheduler nothing per step, in that regime.

**The regime where they do cost.** When admission is blocked by KV memory
instead of by `max_num_seqs` (the priority run), the head of the queue is
evaluated every step: 168 `sched_waiting_eval` for 36 admissions, 132 wasted
evaluations at ~203k each, re-running `get_computed_blocks`
(`kv_cache_manager.py:250`) and `allocate_slots` from scratch. Nothing is
cached across steps; with prefix caching on, the probe alone is 17.5k rather
than 1.2k. That is ~200k per step for as long as the pool stays full.

**Preemption is five linear scans per victim.** 2,140 per running request,
attributed to tuple construction and comparison: `max(self.running, key=...)`
at `scheduler.py:648` builds a fresh 2-tuple per running request, then
`self.running.index()` at 654, `del` at 655, `in scheduled_running_reqs` at
662 and `.remove()` at 664. Every preemption in this run entered with
`preempted=0`, so the multi-victim `while True` loop, which would be
O(running²) per step, was not exercised and is not bounded here.

**Chunked prefill is a flat tax per chunk.** `kv_allocate_slots` costs ~63k
per 127-token chunk against 37.9k per decode token, flat in `num_computed`
(69 to 831) and in prompt length; the prefix probe and the waiting
evaluation run once per request, not per chunk. So a 2k-token prompt pays
about 1.0M in `allocate_slots` over its 16 chunks, ~492 per token, from
chunk count alone.

**Relations** (exact at every trigger):

```
sat    schedule.waiting = count(fcfs_add) - count(fcfs_peek)
       schedule.running = count(fcfs_peek) - cum(sched_remove_all.n_remove)
       update_after_schedule.num_tokens = cum(kv_allocate_slots.num_new_tokens) - cum(execute_model.num_tokens)
prio   count(prio_prepend) = count(sched_preempt) = count(sched_preempt_request)
       schedule.running = count(prio_pop) - count(prio_prepend) - cum(sched_remove_all.n_remove)
```

The second priority relation is the preemption conservation law, running
equals admissions minus preemptions minus finishes, learned from counts.

**Third beat, measured** (`patches/vllm_sched_head.patch`,
`patches/vllm_sched_preempt.patch`, copy `vllm-cpu-schedfix`,
`out/vllm_schedfix_prio`, `out/vllm_schedfix_sat`). Equivalence is stronger
than output text here: a scheduler hook logged, per step, the running queue
in admission order, the preempted ids, the scheduled token counts and the
number of queue peeks, and the logs are byte-identical before and after on
all three workloads, so the control flow is unchanged, not just the result.

```
sched_preempt       2,140.5*running + 94,086.3    14.9%   ->   422.8*running + 98,683.2    9.9%
sched_waiting_eval  triggers 168 -> 59 (36 admissions + 23 forced by real frees); total 23,714,077 -> 10,319,210 (-56.5%)
schedule (prio)     847.6*running + 115*waiting + 22,207    ->   655.5*running + 102.2*waiting + 26,293
schedule (sat)      971.3*running + 0*waiting + 69,720      ->   891.4*running + 0*waiting + 70,841     (unchanged, as expected: no waste there)
```

The memo keys on the request's identity and progress, the free-block count
(an allocation cannot turn a refusal into an admission, only a free can) and
a new generation counter on the prefix-cache map, and is guarded off for
connectors, LoRA, Mamba and speculative paths; 109 of the 132 wasted
evaluations disappear at 122,888 each. The preemption becomes one pass
carrying `(priority, arrival_time)` as scalars with the same first-maximal
tie-break as `max`, and one `del`. At 64 running with the pool full: about
123k per step saved by the memo, plus ~110k per preemption.

**What the residues name.** `schedule` at 94-98% unexplained is the
admission and preemption events themselves, which happen on 35% of steps
independently of `running` and `waiting`; the states that would explain it
are `admitted` and `preempted` on `schedule`. `kv_allocate_slots` at 49%
in the chunked run is the 25k step from one to 127 new tokens landing in
irregular blocks; the state is `ceil(num_new_tokens / block_size)`.

At 64 running and 200 waiting with 2k prompts the affine scheduler tax is
about 2.9M instructions per step, the waiting requests add nothing, and the
two costs that do scale are the ones above: ~200k per step while the pool
is full, and ~1.0M per prompt admitted in chunks.

---

