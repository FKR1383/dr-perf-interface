# First zlib run: 2026-09-15

This run did not produce a successful recovery of a missed feature. The
experimental agent tried five candidate sets and returned to its initial `n`
model, which still left 47.43% of discovery cost unexplained.

This historical run predates the mandatory irregularity target and continuation
policy. Its artifacts are preserved; the current reproduction instructions use
the updated policy and a larger attempt budget.

Both fresh sessions used gpt-6-astra with xhigh reasoning through Codex CLI
0.154.0-alpha.6.2. The target was the real zlib 1.3.1 implementation, compiled
with `-O2 -g`. The fixed discovery and reserved validation workloads each
contained 96 compression calls. Every call passed decompression verification.
See [README.md](README.md) for the exact workload and reproduction commands.

## Agent answers

Agent Only returned `{input, level, n}`. This names the input data dependency,
but `input` is a byte-buffer pointer. The answer does not specify an integer
summary of its contents. Its complete selection cannot be measured directly
under the four-integer-state contract. Validation reports this explicitly;
measuring the pointer address would not measure the contents.

Agent + Dr. Perf recorded:

| Attempt | Selected expressions | Irregularity |
| --- | --- | --- |
| 1 | `n` | 47.43% |
| 2 | `n`, `level` | 99.63% |
| 3 | `n`, `n * (level > 3)` | 97.90% |
| 4 | `n`, `n / strm.state->lit_bufsize` | 96.03% |
| 5 | `n`, `n * n` | 93.17% |

It selected attempt 1. Its displayed model, in instructions per compression, is:

```text
n <= 16384:  10.5*n + 45644.7
n >= 32768:  43.9*n + 147790.4
```

These formulas exclude irregular cost. Each regime has only three observed
sizes. Calls at the same `n` average across four contents and four levels.

The apparently better score for `n` does not show that level is irrelevant:
declaring `level` separates previously averaged calls. In addition, the current
Dr. Perf derivation can split a one-variable fit into two regimes, but does not
split a multivariable fit. These differences limit comparisons based solely on
the lowest irregularity.

## Validation

The validation step fixed the selected expressions and supplied no more agent
feedback. Replaying discovery reproduced its formula and exact irregularity.

- Fitting the same `n` feature on reserved inputs left **46.08% irregularity**.
  This is a new fit, not a prediction from the discovery coefficients.
- Freezing the replayed discovery formula gave **45.00% call-weighted absolute
  percentage error** against validation state means, covering **80 of 96 calls**.
  Error is `sum(calls * abs(predicted - actual)) / sum(calls * actual)` over
  covered state points.
- The remaining 16 calls have `n = 24576`, between the two discovery regimes.
  No boundary was invented to assign these calls a prediction.
- The comparison is against averaged instruction counts. It does not establish
  per-file prediction accuracy. Source/text validation slices also overlap the
  discovery files; this is not an independent-document evaluation.

The static answer's non-integer `input` feature was recorded as unsupported, so
the validation command exits with status 1 while preserving the completed
experimental-agent measurements. There is no complete quantitative comparison
between the two agents for this run.

## Interpretation and evidence

The experiment shows that real compression is harder for this setup than the
earlier parser example. Feedback exposed substantial unexplained work, but the
agent did not find a feature set that resolved it within five attempts. The
run is evidence of an unresolved modeling problem, not of successful discovery
or general superiority of either approach.

Local artifacts (ignored by Git):

- `evaluation/results/zlib-discovery/result.json`: both answers and all attempts.
- `evaluation/results/zlib-discovery/logs/`: source inspection, edits, and feedback.
- `evaluation/results/zlib-discovery/measurements/`: raw instruction measurements.
- `evaluation/results/zlib-validation/validation.json`: validation, prediction
  coverage, and the static-answer limitation.
- `build/evaluation-zlib-validation/provenance.json`: archive checksum and frozen
  workload parameters and file hashes.

A useful next experiment would mark an internal match-search operation, where
algorithm state is available at entry. It should be recorded as a separate
experiment with a new boundary and workload, preserving this unsuccessful run.
