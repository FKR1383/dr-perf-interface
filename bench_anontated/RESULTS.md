# Recorded agent experiment results

207 case exports; 129 cases attempted; 119 have successful target measurements; 43 final annotations pass the gate.

| Group | Cases | Successful target measurements | Final gate passes |
| --- | ---: | ---: | ---: |
| accidental-quadratic | 21 | 20 | 9 |
| v8-interpreter | 50 | 0 | 0 |
| v8-regexp | 28 | 0 | 0 |
| vllm | 67 | 58 | 16 |
| wan | 41 | 41 | 18 |

## Accepted optimizations

| Case | Before instructions | After instructions | Reduction | Optimized model passes 5% gate | Small-state regressions |
| --- | ---: | ---: | ---: | --- | --- |
| [aq-003](../bench_optimized/accidental-quadratic/aq-003/result.json) | 274,390 | 168,438 | 38.61% | Yes | Yes; see per-state evidence |
| [aq-015](../bench_optimized/accidental-quadratic/aq-015/result.json) | 273,667 | 235,906 | 13.80% | Yes | Yes; see per-state evidence |
| [vllm-050](../bench_optimized/vllm/vllm-050/result.json) | 616,760 | 587,249 | 4.78% | Yes | None observed |
| [wan-007](../bench_optimized/wan/wan-007/result.json) | 2,202,615 | 1,694,414 | 23.07% | No; needs further explanation | Yes; see per-state evidence |
| [wan-008](../bench_optimized/wan/wan-008/result.json) | 2,222,457 | 1,699,295 | 23.54% | No; needs further explanation | None observed |

These are total target-region instructions over matching small workloads, not
end-to-end latency improvements or larger-input predictions. Rejected candidates
remain in the optimization directory with `accepted: false`.

The CSV candidate aq-008 was rejected after differential tests found changed
behavior. The vLLM bulk-queue candidate vllm-024 regressed on its measured workload.
Exploratory agents had prior collection context; this is not a blinded accuracy comparison.

See `summary.json` in each experiment directory for every outcome, including
blocked, failed, above-threshold, and unattempted cases. The audit checks that
benchmark files and marked boundaries are preserved and final measurements match source hashes.
