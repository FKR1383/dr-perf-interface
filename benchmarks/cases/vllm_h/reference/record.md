### vLLM case H. n-gram speculative decoding on the CPU backend: the cost function says it cannot pay, and it does not

Marked copy `vllm-cpu-spec/`, `mark_spec.py` (two marker sets, `spec` and
`stop`), driver `examples/vllm_run_spec.py`. Two things had to be fixed before
any of it measured what it claimed to:

- **`--late` attached inside `LLM(...)`.** `NgramProposer.__init__` calls
  `propose()` to prime the numba JIT, so with the `spec` set the first marker of
  the run fires during the model build: DynamoRIO attached there, the rest of the
  load ran instrumented (3m31s instead of 51s), and the JIT of the KMP kernel
  landed inside `ngram_scan` as a single 6,064,741,919-instruction trigger, taking
  `ngram_propose` to 99.9% irregular. The driver now replaces `perfmark.region`
  with a null context manager for the duration of `LLM(...)` **and the warm-up
  generate**, and restores it at `vllm_attach`. Anyone marking a lazily-JIT-ed or
  lazily-initialised path needs the same trick.
- **Every new region carries a constant `tag` state.** The client's fast key
  cache compares region and state-name strings by pointer, so two regions sharing
  a root, a state count and identical state values merge (see the notes below).
  `sample(num_reqs=8)` and `engine_step(unfinished=8)` are exactly that pair in
  steady-state decode, as are `update_from_output(8,0,0)` and
  `update_states(8,0,0)` once `num_draft` is declared. Tags 9001..9018 make the
  value tuples unique. All runs below print zero "perfmark_end without matching
  begin".

```
export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-spec:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
export VLLM_CPU_OMP_THREADS_BIND=all OMP_NUM_THREADS=8
python mark_spec.py vllm-cpu-spec spec          # or: ... stop
/home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \
    --max-slots 2097152 -o out/vllm_spec_k3 \
    -- <venv>/python examples/vllm_run_spec.py mode=spec reqs=8 k=3
```

Eight requests, `facebook/opt-125m`, staggered `max_tokens` 64..22 so the batch
drains one request at a time; half the prompts repeat a phrase, half do not.
Runs: `out/vllm_spec_k3`, `_k5`, `_plain` (control), `_long` (~640-token
prompts), `_mix`/`_mix5` (`pfam=1`, random-number prompts so the lookup misses).

```
ngram_scan         cost(num_valid, ctx, k, tag) = 9,926.9*num_valid + 18*ctx + 0*k + 24,536.1        6.6% irregular
                       per ctx: 25.1 <no module> (the numba KMP kernel)
ngram_propose      cost(num_reqs, k, ctx, tag) = 7,717.2*num_reqs + 0*k + 6.6*ctx + 213,274.3       13.6%
ngram_gather       cost(num_reqs, num_valid, tag) = 1,961*num_reqs + 3,086.7*num_valid + 240.3       2.1%
                       per num_reqs: 423.1 _PyEval_EvalFrameDefault, 338.3 PyObject_RichCompareBool
reject_sample      cost(num_reqs, num_draft, max_spec, tag) = 1,107,763.8*num_reqs + 1,127,991.2*num_draft + 412,557.4   8.0%
                       per num_draft: 703,812.6 + 402,204.6 c10::function_ref<...>::callback
sample             cost(num_reqs, tag) = 704,436*num_reqs + 91,492.9                                17.7%
                       per num_reqs: 703,897.2 c10::function_ref<...>::callback
execute_model      cost(num_tokens, num_reqs) = 117,149,875.2*num_tokens + 2,449,800.1*num_reqs + 1,116,215,516.6   2.4%
update_from_output cost(running, num_draft, num_accepted, tag) = 24,722.9*running + 3,104.8*num_draft + 0*num_accepted + 43,589.8   25.0%
update_states      cost(num_reqs, num_new, num_draft, tag) = -3,418.9*num_reqs + 139,104.7*num_new + 2,625.1*num_draft + 98,271.3  19.6%
prepare_inputs     cost(num_reqs, num_tokens, num_draft, tag) = 42,167.6*num_reqs - 416.4*num_tokens - 11,516.5*num_draft + 794,596.8  1.1%
```

**Speculation cannot pay here, and the forward's cost function says so before
you run it.** `execute_model` measured per call: 1,455,869,529 for 8 scored
tokens (plain), 5,654,179,627 for 32 (K=3), 8,455,452,379 for 48 (K=5) — that
is 182.0M, 176.7M and 176.2M instructions **per scored token**. The CPU forward
has a 3.2% economy of scale between 8 and 48 tokens per step, and none beyond.
An n-gram draft of K tokens scores K+1 to emit at most K+1, so the whole upside
is that 3.2%. On the debit side `reject_sample` charges 1,127,991 per draft
token where `sample` charges 704,436 per row, so sampling per output token goes
704k to 1,136k, +61%. Measured, same 344 tokens: plain 70.5 tok/s, K=3 73.2,
K=5 73.2; total instructions `generate_loop` 24.322 G (plain), 24.791 G (K=3),
24.143 G (K=5). A wash, exactly as the two coefficients predict. This is a GPU
optimisation ported to a backend whose arithmetic does not support it, and the
formula is the cheapest possible way to see that.

**The proposer rescans the entire context every step.** Fitting `ngram_scan`'s
own-thread cost across all six runs (num_valid 1..8, ctx 250..6,431):

```
ngram_scan self = 9,822*num_valid + 22.9*ctx + 33,258     max residual 1.1%
```

`ctx` is the sum of the context lengths of the requests scanned, so this is 23
instructions per token of history, per step, forever. The KMP loop in
`_find_longest_matched_ngram_and_propose_tokens`
(`ngram_proposer.py:263-296`) walks `origin_tokens[::-1]` from index 1 to
`total_token` every call; its answer depends only on the last `max_ngram`
tokens and on where they previously occurred, both of which an incremental
index would carry across steps. `learn` states it as a conservation law:
`ngram_scan.ctx = cumend(ngram_scan.ctx) - 296`, exact at 17/17 triggers.

**`ngram_gather` is quadratic in the batch.** `if i in valid_ngram_requests`
(`ngram_proposer.py:131`) is a list membership test inside a loop over all
requests. Fitting the per-call cost at num_reqs = num_valid = n:

```
quadratic  69.6*n^2 + 4,577*n + 1,553     max residual   61  (0.15%)
linear                5,197*n +   522     max residual  526  (1.2%)
```

`PyObject_RichCompareBool` at 338.3 per request is the scan. At n = 64 the
quadratic term is 285k of 580k instructions per step. `valid_ngram_requests` is
built as a sorted list of indices; a `set`, or zipping the loop against it,
removes the term.

**Acceptance.** With repetitive prompts and greedy decoding on a 125M model
every draft is accepted, and `learn` says so exactly:
`update_from_output.num_accepted = last(prepare_inputs.num_draft)` at 17/17
triggers in `out/vllm_spec_k3`. With random-number prompts (`pfam=1`,
`out/vllm_spec_mix`) the relation breaks and least squares gives
`num_accepted ~ 0.726*last(prepare_inputs.num_draft)` (R^2 0.999). `ngram_scan`
costs the same either way: the scan runs for every request that has a sampled
token, whether or not it will produce a usable draft. That decoupling — the
cost proportional to context, the benefit proportional to acceptance — is what
the two formulas make explicit.

At 64 requests with 1,000-token contexts and K=5, per step: `ngram_scan`
2.13M, `ngram_gather` 0.55M, `reject_sample` 1,107,764*64 + 1,127,991*320 =
432M, against a forward of 176M * 384 = 67.6G. The proposer is noise; the
rejection sampler is 0.6%; the forward is everything, and it is 6x what the
same 64 tokens would have cost without speculation unless acceptance is near
perfect.

**Third beat for the scan, measured** (`patches/vllm_ngram_index.patch`,
`out/vllm_spec_fix_*`, `out/bench_ngram_prod`). Reading the kernel first
mattered: KMP over the reversed context with `>=` updates selects the
*earliest* earlier occurrence of the longest matching suffix, not the most
recent, and a first-occurrence table never changes in an append-only
history, so it reproduces the rule exactly. Per (request, n-gram length) an
open-addressed table of first occurrences, confirmed against the tokens, is
extended by the newly appended tokens each step; a pure-Python index was
tried and rejected at 63.7k per request per step. Equivalence: 32,711
proposals identical across the stock kernel, a brute-force oracle and the
index over 1,500 randomised histories, and byte-identical draft logs and
outputs on all four spec workloads.

```
ngram_scan   before  9,856*num_valid + 22.9*ctx + 32,441   (1.4%)
             after   11,909*num_valid + 0.9*ctx + 34,705   (3.3%), plus a build of ~300 per token indexed, once per request
ngram_gather the 56.4*n^2 term is gone (`set` instead of a list scan)
64 requests x 1,000 tokens, K=5, measured side by side:  ngram_scan 2,125,389 -> 881,113 per step; gather 436,236 -> 221,638
```

A 1.46M per-step saving against a 19.4M one-time build breaks even after
16 steps, so the short driver runs are a wash to worse and the win is
steady-state decode; against the 67.6 G forward per step it remains noise,
which is what case H said the cost function implied before any of this was
built.

