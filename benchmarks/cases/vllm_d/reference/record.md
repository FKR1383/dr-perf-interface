### vLLM case D. Sampling with penalties: a per-step cost that grows with everything generated so far

Same prompts, two modes, driver `examples/vllm_run_samp.py` with markers from
`examples/mark_samp.py`: greedy (`out/vllm_samp_greedy`) and penalised
(`temperature 0.7, top_k 40, top_p 0.9, repetition 1.2, frequency 0.5,
presence 0.3`, `out/vllm_samp_pen`). Twelve requests, output lengths 16..96,
672 generated tokens in both.

```
penalised
sample            cost(num_reqs) = 31,190,378.7*num_reqs + 1,029,802.3                                                     7.9% irregular
topk_topp         cost(num_reqs, k, p_flag) = 27,849,583.1*num_reqs + 0*k + 0*p_flag + 471,687                             8.3%
    per-request: std::__introsort_loop 6,851,396, __log1p_fma 6,532,525, at::CPUGeneratorImpl::random64 5,726,822
logitsprocs       cost(num_reqs) = 3,342,904.9*num_reqs + 443,222.2                                                        6.3%
apply_penalties   cost(num_reqs, max_len, total_tokens) = 2,657,744.8*num_reqs + 2.7*max_len + 352.9*total_tokens + 412,343.9   21.0%
pen_tensors       cost(num_reqs, max_len, total_tokens) = 3,299.1*num_reqs - 3*max_len + 309.9*total_tokens + 29,953.4      5.1%
    per-total_tokens: PyArray_Pack 69, PyArray_DiscoverDTypeAndShape_Recursive 64, LONG_setitem 57
greedy
sample            cost(num_reqs) = 740,547.9*num_reqs + 545,467.7   [num_reqs >= 6]                                        0.0%
```

**The quadratic.** `pen_tensors` is the padded tensor of every request's
output token ids, rebuilt every step (`penalties.py:47` into
`torch_utils.py:731`, `padded_x[ind, :len] = blocktb`), and it costs 309.9
instructions per token already generated, in numpy's element-by-element
conversion; `apply_penalties` adds ~43 per token for the `scatter_add_`.
`learn` supplies the proof that this is history and not batch size:

```
apply_penalties.max_len = count(apply_penalties) - 2*count(generate_loop) + 2
```

the padded width is the step index, exactly, at every trigger. So the
per-step cost of penalties is `353 x (tokens generated so far by all
requests)`, which sums to a quadratic over a generation. At 64 requests
generating 1,000 tokens the last step pays 22.6M instructions and the
generation about 1.1 x 10^10, to re-encode a history that changed by 64
tokens. This tensor is built on the host in both backends; only the
vocabulary-sized kernels below are CPU-specific figures.

**Per-request, penalised is 42x greedy.** `sample` is 740k per request per
step greedy and 31.2M penalised. 27.85M of that is `topk_topp`: a full sort
of the 50,272-entry vocabulary (`topk_topp_sampler.py:388`) plus `log1p` and
`random64` exponential noise over the whole vocabulary per request, for a
top-k of 40. On this backend the sampler, not the model, is the step at
scale: ~2 x 10^12 instructions of sampling against 4.7 x 10^10 greedy for
64 x 1,000.

**Third beat, measured** (`patches/vllm_penalties.patch`, `out/vllm_samp_pen_fix`;
token ids and text of all twelve requests byte-identical by SHA-256):

```
pen_tensors       before  3,299.1*num_reqs - 3*max_len + 309.9*total_tokens + 29,953.4     5.1% irregular
                  after     376.8*num_reqs + 0*max_len +   3.0*total_tokens + 29,213.6    66.7%
apply_penalties   before  2,657,744.8*num_reqs + 2.7*max_len + 352.9*total_tokens + 412,343.9
                  after   2,654,584.5*num_reqs + 2.0*max_len +  50.2*total_tokens + 370,733.1
```

One file changed, `penalties.py`: a per-request int64 array cached by the
identity of its output-token list, extended by the newly appended tokens
each step, with the padded matrix filled by row copies. The per-token
column that read `PyArray_Pack`, `DiscoverDTypeAndShape`, `LONG_setitem`,
`PyLong_AsLong` before reads one function after, a strided memcpy at 3.0
per token. The coefficient the second beat pointed at is the one that
moved, by two orders of magnitude, and nothing else did (`sample` is
31.19M then 31.20M per request). On this twelve-request workload the saving
is 0.02% of the loop, invisible in wall time; at 64 x 1,000 the formula
puts the final step at 0.25M instead of 20M and the run at 0.15 G instead
of 10.2 G, and the quadratic term is gone. The 66.7% irregular after the
change is the cache hit/miss branch, now the only thing left in a region
that costs a tenth of what it did.

**A negative result worth having.** The survey expected `_make_sampling_metadata`
to be rebuilt per step; it is called 8 times in 98 steps, only on batch
change, and `max_prompt` carries a negative coefficient in the greedy run.
The per-step metadata cost is `refresh_metadata`'s ~51k constant, not a
rebuild. The measurement corrected the reading of the code.

**Relations** (`out/vllm_samp_pen/learn.txt`): `topk_topp.num_reqs = last(apply_penalties.num_reqs) = last(sample.num_reqs) = last(engine_step.unfinished)`,
`pen_tensors.total_tokens = last(apply_penalties.total_tokens)`, and the
`max_len` identity above, which chain every sampling coefficient to batch
occupancy and step index, so the sampler's cost for any workload is a
calculation rather than a run.

One stock-vLLM issue met on the way, not caused by the markers: with chunked
prefill and per-request seeds the CPU backend crashes in
`gpu_model_runner.py:3826` (`gen.get_offset()`, "CPU Generator does not use
offset"); `max_num_batched_tokens=2048` avoids it.

---

