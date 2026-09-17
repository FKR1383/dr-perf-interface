### vLLM case H2. Stop strings are free, `min_tokens` is free, and one request's `logprobs=5` bills the whole batch

Second marker set (`python mark_spec.py vllm-cpu-spec stop`), driver modes
`stop` (stop strings on all eight requests, `logprobs=5` on half,
`min_tokens=8` on two, `max_tokens` 128 staggered) and `splain` (control).
`out/vllm_stop`, `out/vllm_splain`, `out/vllm_stop_long` (`max_tokens=384`).

```
check_stop        cost(have, new_chars, nstop, tag) = 0*have + 0*new_chars + 0*nstop + 4,196.8    0.0% irregular
detok_update      cost(num_new, have, toks, tag) = 0*num_new + 0*have + 5.1*toks + 28,113.8      53.8%
logprobs_update   cost(num_logprobs, num_new, have, tag) = 0*... + 289,681.3                     72.7%
gather_logprobs   cost(num_reqs, num_logprobs, tag) = 1,009,495.2*num_reqs + 115,043.4           57.2%
                      per num_reqs: 913,749.3 at::native::AVX2::topk_impl_loop, 88,004 kernel._omp_fn.0
min_tokens_apply  cost(num_reqs, num_affected, tag) = 0*num_reqs + 16,785.7*num_affected + 174    0.0%
logit_bias_apply  cost(num_reqs, num_affected, tag) = 0*num_reqs + 0*num_affected + 138.7         0.0%
sample            cost(num_reqs, tag) = 707,856*num_reqs + 151,166                               79.7%
```

**The stop-string quadratic is gone in 0.28.** `check_stop` is 4,196.8
instructions per call with `0*have` at **0.0% irregular**, and the same
4,211.4 at `max_tokens=384` where `output_text` reaches ~1,900 characters.
`check_stop_strings` starts its `str.find` at `1 - new_char_count -
len(stop_str)` (`detokenizer.py:340`), so it only ever searches the new tail.
The earlier note in this document pointing at a suffix-slice quadratic around
`detokenizer.py:161` should be read as applying to `get_next_output_text`,
which in `FINAL_ONLY` runs once per request, not per step.

**What does grow is `detok_update`, at 5.1 instructions per output token so
far** — the same coefficient at 128 and at 384 output tokens, attributed
entirely to `_PyEval_EvalFrameDefault`, i.e. `self.output_text += ...`
(`detokenizer.py:120`) rebuilding the string each token. 5,100 per step per
request at 1,000 tokens, 2.55M over the request's life. Real, and small.

**`min_tokens` and `logit_bias` cost nothing when unused**: 174 and 138.7
instructions flat, 0.0% irregular, and 16,785.7 per *affected* request when
`min_tokens` is live. No reason to gate them out.

**One request's `logprobs` bills every row.**
`InputBatch.max_num_logprobs` is `max(self.num_logprobs.values())`
(`gpu_input_batch.py:1150-1151`), so `Sampler.forward` runs `log_softmax` and
`torch.topk` over the whole `[num_reqs, 50272]` matrix as soon as one request
sets `logprobs=k`. `learn` states it exactly:

```
gather_logprobs.num_reqs = last(engine_step.unfinished)   exact at 118/118 triggers
```

with only four of the eight requests asking. Natively, half a batch costs the
same as a whole one: `mode=stop max_tokens=128`, 744 tokens, `lp=0` 105.1 tok/s,
`lp=1` (half) 86.1, `lp=2` (all) 85.9.

**The optimise beat.** `patches/vllm_stop.patch`
(`patches/apply_logprobs_rows.py <tree>` applies it; base sources in
`patches/base_stop/`): `InputBatch` publishes the row indices that asked, and
`Sampler` runs the top-k on those rows and scatters the result back into a
full-height tensor. The rows nobody asked about are left at zero and are never
read — `Scheduler.update_from_output` slices `logprobs` per request only when
`sampling_params.num_logprobs is not None` (`scheduler.py:1988-1994`).

```
                       before (out/vllm_stop)                after (out/vllm_stop_after)
gather_logprobs states num_reqs = 2,3,4,5,6,7,8              num_reqs = 1,2,3,4
steady-state row       total/call     64,131,276             59,409,231     -7.4%
  of which other-thr   16,205,197                            11,489,509    -29.1%
  of which own-thr     47,926,078 (OpenMP pool spin)         47,919,723      0.0%
sample self (whole run)   186,894,327                       218,877,207    +17.1%
```

The per-row top-k is ~1.18M instructions and it lives entirely on the OpenMP
worker threads (own-thread cost is flat at 1.29-1.32M per call for one row or
seven); halving the rows removes exactly four of them,
16.21M -> 11.49M = 6.8M + 1.18M*rows. The `sample` increase is the added
`logprobs[rows]` gather and the three `index_copy_` scatters, 250k per call.

Outputs are byte-identical: token ids, text, finish and stop reason,
cumulative logprob and the full top-5 logprob dicts with decoded tokens and
ranks, dumped with `SPEC_DUMP=` and compared —
`lp=0/1/2` and `mode=spec` all match (`sha256 54d35feb5988...` for `lp=1`
before and after).

**And the beat does not move the clock.** Alternating before/after, three
pairs: 85.3/85.7, 84.0/85.9, 85.9/85.8 tok/s. There are eight OpenMP threads
and four rows removed, so the top-k finishes in the same wall time with half
the work. The formula bought a 29% reduction in the region's instruction count
and a correct statement of when it would matter — at 64 requests with 8 asking
it is 56 * 1.18M = 66M instructions per step — but nothing measurable at this
batch size. That is the honest shape of this fix, and it is a shape a
wall-clock profiler cannot express at all: the profiler would have shown the
top-k at 1.2% of wall and stopped.

**Where the time actually is.** Summing the trace, `execute_model` is 96.4% of
`generate_loop` in the plain run, 97.0% with K=3, and 87.1% in the logprobs
run. Every host-side region marked in cases G and H together is inside the
remaining 3%. That is the finding that should govern what gets optimised next
on this backend, and it took one `derive` to establish.

---

