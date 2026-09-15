# vllm-024 growth experiment

The guarded bulk-heapify candidate is accepted for an empty destination and a
strict-descending batch of at least 512 requests. It reduces target instructions
4.89–5.58x at 512–1,000 items. Ascending and deterministic mixed controls retain
the original insertion path and cost 0.6–1.8% more instructions from bounded
classification overhead.
Both baseline and optimized DrPerf models pass the five-percent gate and their
independently computed numeric reconstruction errors are below two percent.

The native test covers sizes 16–1,024, empty queues, existing items, equal
priority/arrival ties, self-aliasing, exact order, identity, and multiplicity:

```sh
/home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python tests/test_case.py --source-root /home/ubuntu/drperf/bench_optimized/growth-multifold/vllm-024 --profile all
```

Real DrPerf rounds retain exact invocations, raw traces, metrics, feedback, and
output. Earlier integer/custom-Batch rounds are explicitly rejected surrogate
evidence. Final measurements use `FCFSRequestQueue` input, `PriorityRequestQueue`
destination, and a comparator copied exactly from pinned `Request.__lt__`. The
differential receipt also checks incoming lengths 1–8 against an existing
10,000-item heap and observes zero `heapq.heapify` calls.
The eight-item prefix classification is a heuristic: performance claims apply
only to the measured strict-descending matrix, while misleading-tail scenarios
provide correctness evidence only.
