# Agent annotation experiments

For every exported region, sorted with successful annotations first, see the
[complete code review](review/annotated-regions.md) or the
[searchable HTML document](review/annotated-regions.html). These include the
expanded workloads alongside the original trials and distinguish annotation
results from optimization results. Regenerate them with
`python3 bench_anontated/review/generate.py`.

See [RESULTS.md](RESULTS.md) for coverage and measured optimization outcomes,
and [summary.json](summary.json) for every case's status.

This directory uses the requested spelling `bench_anontated`. It contains
independent exports of the source-region benchmark at commit `a5b7868`.
`benchmarks/` is read-only throughout these experiments; its pre-run hashes are
recorded in `benchmark-snapshot.json`.

Agents first annotate a region using real drperf feedback. Optimization starts
only after the annotation qualifies, and goes in `../bench_optimized/`.
These are exploratory development runs: the agents helped collect these cases
and have prior project context. They are not a blinded agent-accuracy evaluation
or a comparison with agents lacking drperf.

## Protocol

- At most three annotation attempts per case, with a 120-second process budget
  for each instrumented workload. Infrastructure checks and corrective reruns
  must be recorded separately when needed.
- Preserve the marked region's boundary and program behavior. PCVs are at most
  four cheap expressions of state available at entry. Do not encode measured
  cost, move work outside the marker, or remove difficult test inputs.
- Small input matrices may be expanded in the experimental copy to provide
  enough distinct states. Retain correctness assertions and record changes.
- Require at least `max(3, number_of_PCVs + 2)` observed state points. A single
  aggregated state or an absent formula cannot qualify.
- Fit one affine interface in the declared expressions, without automatic
  regime splitting. Keep the checker's existing block tolerances: 5% relative
  plus 64 instructions absolute.
- Qualify only when unexplained instructions are at most 5% of the counted
  instructions at **every observed state**, with successful correctness checks,
  clean drperf validity checks, no dropped target calls, and no nested marked
  regions excluding work. This is an observed-state gate, not a universal proof.
- Keep failures, unresolved dependencies, insufficient-state outcomes, and
  above-threshold results. Do not infer success from absence of a printed warning.

## Files and reproduction

Each `<group>/<case>/` contains its exported source, test bundle, and a
`result.json` describing the outcome. Attempt directories retain commands,
source hashes, stdout/stderr, formulas, attribution, and numerical metrics.
The exported `case.json` retains the original upstream source identity; the
changed source, `annotation.patch`, and `result.json` describe the agent's final
annotation. The original snapshot hash is not a hash of the modified source.
`annotation.patch` records changes to the empty-marked source when supplied.
Large runtime checkouts and raw DynamoRIO records stay local and are ignored by
Git; compact feedback and measurements are retained for review. A case with
`blocked-runtime` has an export but no successful annotation measurement.

Run an instrumented attempt with a new output directory:

```sh
python3 bench_anontated/measure.py run \
  --case aq-001 --workspace /absolute/path/to/case \
  --out /absolute/path/to/case/attempt-01 --timeout 120 -- \
  python3 tests/test_case.py --source-root /absolute/path/to/source
```

The workload return code and `metrics.json: gate_pass` are separate: a program
can run correctly while its annotation fails. Source-root arguments for large
projects must point to an isolated pinned checkout with this case's changes.
The exported test observer forwards to real PerfMark under the runner's
`DRPERF` environment.

Recorded instruction counts include marker overhead and exclude the checker's
configured runtime-waiting modules. They describe target-region work, not the
entire process. Instrumented wall time includes profiling overhead and is not
an application-speedup metric. Concurrent agents can also perturb native timing.

The 78 V8 cases require a shell built from their pinned source with each C++
marker. No such binary was found in the available project/runtime trees; those
cases are recorded as blocked. Host Node is not substituted for this measurement.

Rebuild the indexes and validate the retained evidence with:

```sh
python3 bench_anontated/summarize.py
python3 bench_anontated/audit.py
python3 -m unittest discover -s bench_anontated -p test_measure.py -v
```

The audit compares the annotated source with the original empty-marked AST,
checks that accepted optimizations keep all changes inside the marker, and
checks final source/test hashes against measurement invocations. Synthetic
gate tests are harness verification only and are not benchmark measurements.
