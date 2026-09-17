# Agent optimization experiments

See [the results table](../bench_anontated/RESULTS.md) and
[the complete status index](summary.json).

These are independent optimization copies of qualifying experiments from
`../bench_anontated/`. The original `benchmarks/` collection is unchanged.

An optimization must preserve behavior and use the same workload and region
boundary as its annotated baseline. Keep correctness results, the source patch,
and before/after drperf instruction counts. Report reductions per state and over
the same call sequence; changing inputs or invocation counts is not a speedup.
Include annotation-evaluation overhead in native timing when reporting practical
performance. A change with no measured benefit should not be presented as an
improvement.

The annotation gate is at most 5% unexplained cost at each observed state, enough
states for the affine fit, and valid traces. Failing or blocked annotations do
not proceed to optimization. Their `result.json` records explain why no optimized
source is present. A qualifying annotation does not guarantee that a useful
optimization exists.

Instruction reductions apply to the measured regions and tested small inputs.
They do not establish end-to-end latency, larger-input behavior, or agent accuracy.
Native timings, where supplied, are separate from instrumented wall time and
must be interpreted with their repeat counts and concurrent-machine noise.
