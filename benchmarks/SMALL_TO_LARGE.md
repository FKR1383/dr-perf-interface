# Symbolic discovery from small inputs

Test the hypothesis that drperf helps an agent discover a dependency from small
executions that time-based profiling only reveals after larger or longer runs.
The experiment must allow this hypothesis to fail: instrumentation can cost
more than the native large run, and a small-case fit can extrapolate incorrectly.

## Design

Use the same agent, source, fixtures, seeds and adaptive measurement budget for
the primary pair. Both agents may inspect code and compute derived PCVs. They
may only execute workloads inside a predefined small-input envelope:

| Arm | Agent measurements | Purpose |
| --- | --- | --- |
| Small timing | Small inputs, time-based profiling | Primary control |
| Small drperf | Same small inputs, timing or drperf | Test symbolic insight from small executions |
| Expanding timing | Predefined ladder of increasing sizes, time-based profiling | Separate follow-up: how much execution was needed to reach the same accuracy? |

Do not combine the expanding-input arm with the equal-input accuracy comparison.
Its input access differs and it answers a different question. Run it in a fresh
session without access to either primary agent's answer or evaluator feedback.
Keep agent model/token limits comparable and record any extra rounds explicitly.

Before the study, choose small inputs that can distinguish competing PCVs:
vary independent dimensions, exercise branch conditions, and cross relevant
small thresholds. Also retain challenge cases whose large-only regimes cannot
be inferred confidently from small measurements. Do not silently remove those
failures or present a new large-input algorithm/cache regime as ordinary scaling.

Freeze the final source annotations, PCV expressions, claims and scope before
revealing any large measurements. The evaluator fits coefficients using only
small-input counts, then freezes them too. Agents need not supply coefficients.
Large inputs are reserved for testing; they must never repair the submitted
basis, coefficients or claimed regime.

## Outcomes

Report these separately:

- **PCV discovery accuracy:** correct dependencies, expressions and locations,
  including unsupported extra claims, using the paired scorer after each round.
- **Transfer to larger inputs:** whether the frozen expressions explain the
  larger executions, unexplained instruction share, and prediction error with
  coefficients frozen from small inputs. A quadratic insight can be correct
  while an absolute count prediction is inaccurate; show both.
- **Execution cost to reach a fixed accuracy:** total profiling wall time,
  process launches, largest input attempted, timeouts, and CPU/GPU resource
  usage. Include drperf instrumentation, initialization, and unsuccessful runs.
- **Avoided large agent runs:** how many expanding-timing executions were needed
  to reach the same correctness, and the difference in cumulative execution
  cost. Report failure to reach that accuracy as censored, not as zero cost or
  an infinite speedup.

The evaluator still runs large cases to establish ground truth. Record that
expense separately; any saving claimed here concerns the agent's discovery
workflow, not eliminating the study's validation work. A held-out success
supports transfer on those executions, not an all-input performance guarantee.
Instruction counts and wall-clock latency remain distinct: a host-cost formula
does not establish GPU latency scaling or end-to-end speedup.

## SQLGlot pilot

```sh
python3 benchmarks/bench.py prepare sqlglot /tmp/sqlglot-small-timing \
  --archive /home/ubuntu/drperf-cases --condition timing --track small-to-large
python3 benchmarks/bench.py prepare sqlglot /tmp/sqlglot-small-drperf \
  --archive /home/ubuntu/drperf-cases --condition drperf --track small-to-large
```

The supervisor allows only explicit integer `n_joins` values from 2 through 32.
It rejects omitted dimensions (which otherwise invoke larger driver defaults),
unknown arguments, and oversized inputs before launching a workload. It records
the track with measurement results and submissions. The scorer rejects mixing
tracks in one comparison. Container isolation and review of agent changes are
still needed to prevent bypassing the supervisor through edits or direct runs.

The evaluator-only [pilot plan](evaluator/small-to-large/sqlglot.json) proposes
larger sizes and a timing size ladder. Those are experiment design choices,
not measured results or a reviewed oracle. Keep that plan out of agent exports.
Wan and vLLM require their own jointly bounded shape/request/history envelopes;
they are not enabled in this track yet.

Implemented now: track selection, small-input enforcement, frozen submission
records, track-aware paired semantic scoring, and an evaluator plan. Still
needed before reporting this claim: executable held-out evaluation, the
expanding-timing arm, resource accounting beyond process wall time, and actual
agent trials. No extrapolation accuracy or saved execution time is claimed yet.
