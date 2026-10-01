# Two-agent PCV evaluation

This directory runs a manual, blinded loop for evaluating how many attempts an
agent needs to discover performance-critical variables (PCVs) for a marked code
region.

The roles are deliberately asymmetric:

1. **Agent 1 (selector)** sees clean source, the neutral task, tests, and its
   own prior candidates. It proposes PCVs and annotates the existing marker. It
   cannot use Dr. Perf. After a valid failed attempt it receives only one
   measurement value: the irregularity percentage.
2. **Agent 2 (measurer)** can use Dr. Perf on the immutable submitted snapshot.
   It does not select PCVs. A trusted Python controller reads Dr. Perf's metrics,
   makes the pass/fail decision, and redacts feedback before Agent 1 sees it.

Success means that the **maximum unexplained-instruction share over every
observed state is strictly less than 10%**. A valid result also requires a
successful workload, clean Dr. Perf validity checks, no dropped target calls,
no nested marked region excluding target work, and at least
`max(3, number_of_PCvs + 2)` distinct states. The PCV names recorded by Dr. Perf
must exactly match the submitted set. This is an observed-state
instruction-count result, not a latency result or a proof for unseen inputs.

## Why cases are restaged

The requested cases live in `bench_anontated` (the repository intentionally
uses that spelling), but that directory contains prior answers, formulas, and
Dr. Perf feedback. Exposing it to Agent 1 would leak the target. `start` accepts
only case IDs present there, then uses `benchmarks/regions/collect.py` to export
the corresponding pristine source with an empty marker and no reference notes.
All 207 unique annotated case IDs currently have such a clean export.

## WAN suite

`wan_suite.py` stages every WAN case from `bench_anontated/wan` without modifying it, strips existing PCVs, expands the shared workload to six bounded configurations, and validates `tests/test_case.py` against the pinned Diffusers revision.

```sh
python3 evaluation/wan_suite.py prepare-all /tmp/wan-evaluation \
  --runtime-template /tmp/diffusers-checkout \
  --python /path/to/venv/bin/python --max-iterations 10
python3 evaluation/wan_suite.py submit wan-001 /tmp/wan-evaluation
python3 evaluation/wan_suite.py measure wan-001 /tmp/wan-evaluation
python3 evaluation/wan_suite.py report /tmp/wan-evaluation
```

The report action writes result-only JSON, CSV, and Markdown tables containing every candidate, irregularity, iteration count, and final result.

## One evaluation

Build Dr. Perf first if it is not already built:

```sh
./build.sh
```

List eligible cases and create a run outside the repository:

```sh
python3 evaluation/evaluate.py list
python3 evaluation/evaluate.py start aq-001 /tmp/drperf-evaluation/aq-001
```

Give Agent 1 only this directory:

```text
/tmp/drperf-evaluation/aq-001/selector/
```

Start it with `selector/PROMPT.md`. It edits the marked source under
`selector/workspace/` and fills in `selector/workspace/CANDIDATE.json`. Then the
human/controller snapshots its candidate:

```sh
python3 evaluation/evaluate.py submit /tmp/drperf-evaluation/aq-001
```

Start Agent 2 separately with `measurement-agent/PROMPT.md`, or perform its
deterministic action directly:

```sh
python3 evaluation/evaluate.py measure /tmp/drperf-evaluation/aq-001
```

If the measurement is valid and below 10%, the run is complete. Otherwise,
continue Agent 1 with the refreshed `selector/PROMPT.md` and
`selector/feedback.json`, have it replace the annotation and candidate, and
repeat `submit` then `measure`.

Inspect the count and percentages at any time:

```sh
python3 evaluation/evaluate.py status /tmp/drperf-evaluation/aq-001
```

`summary.json` records `iterations_evaluated` and `success_iteration`. A
workload or measurement infrastructure failure does not consume a new PCV
iteration; the same immutable submission can be measured again. An analyzable
submission with insufficient states or another candidate-level validity failure
does consume an iteration.

The loop is uncapped by default. A safety cap and other defaults can be changed when starting a run:

```sh
python3 evaluation/evaluate.py start aq-001 /tmp/run \
  --threshold 10 --max-iterations 10 --max-pcvs 4 \
  --python /path/to/venv/bin/python
```

For a workload needing a special invocation, Agent 2 can override the manifest
command after `--`. The command must import or execute the submitted snapshot,
not an unannotated checkout:

```sh
python3 evaluation/evaluate.py measure /tmp/run --timeout 180 -- \
  /path/to/python tests/test_case.py --source-root /tmp/run/attempts/iteration-001/workspace
```

## Isolation requirements

The artifact boundary is enforced: Agent 1's workspace starts clean; tests and
case metadata are hash-protected; submissions are immutable and hashed; full
measurement data stays below `attempts/`; only redacted feedback is copied into
`selector/`.

Filesystem isolation must still be provided by the process runner. A prompt or
working directory alone is not a security boundary because many coding agents
can read parent directories. For a blinded result, run Agent 1 in a container,
VM, or restricted account that mounts only `<run>/selector` and does not contain
Dr. Perf, the repository, Git history, `bench_anontated`, or sibling runs. Do
not enable web search for Agent 1. Agent 2 and the human controller may see the
repository and the rest of the run.

Before publishing a result, manually review each `annotation.diff`. The harness
prevents changes to bundled tests and other original files, but semantic review
is still needed to confirm that a PCV is cheap entry state, the region boundary
and behavior were preserved, and the expression does not encode measured cost.

## Run layout

```text
<run>/
  selector/                    only directory exposed to Agent 1
    PROMPT.md
    feedback.json              percentage only after valid measurements
    workspace/                 clean case plus the current candidate
  measurement-agent/PROMPT.md  instructions for Agent 2
  controller/                  private baseline and state
  attempts/iteration-NNN/      immutable candidate and full measurement data
  summary.json                 iteration count and public outcomes
```

## Tests

The unit tests do not run DynamoRIO:

```sh
python3 -m unittest discover -s evaluation -p 'test_*.py' -v
```

## Full-feedback Agent-PCVs protocol

The publication-oriented protocol uses one isolated, tool-free Agent-PCVs
thread per case.  The same thread persists only across that case's iterations.
There is no measurement agent: a trusted deterministic evaluator accepts the
agent's JSON, validates and inserts 1--4 PCVs, runs Dr. Perf, returns the full
metrics report, and applies the strict `irregularity_percent < 10.0` decision.
The workload and marker remain fixed across at most 10 measured iterations.

Run the complete full-feedback vLLM suite with repository defaults:

```sh
./bench_correct_feedback/run_vllm.sh
```

Run the scalar-irregularity comparison, which uses the same deterministic
measurement script. Valid measurements expose only the numeric percentage;
unscorable measurements expose only sanitized validity reasons instead of a
fabricated percentage:

```sh
./bench_correct_irregularity/run_vllm.sh
```

The same interface supports `wan`, `accidental-quadratic`,
`growth-multifold`, `v8-interpreter`, and `v8-regexp`. See the READMEs in
`bench_correct_feedback/` and `bench_correct_irregularity/` for runtime
requirements, per-suite runner names, reports, and the scalar-v2 fresh-root
rule.

Read status or audit isolation without launching measurements:

```sh
./bench_correct_feedback/status.sh
./bench_correct_feedback/audit_isolation.sh
./bench_correct_irregularity/status.sh
./bench_correct_irregularity/audit_isolation.sh
```

Run only one case:

```sh
python3 evaluation/run_agent_pcvs.py vllm --case vllm-005 \
  --root /tmp/full-feedback/vllm
```

To replace Agent-PCVs with a manually obtained response, prepare without
starting an agent:

```sh
python3 evaluation/run_agent_pcvs.py vllm --case vllm-005 --prepare-only \
  --root /tmp/manual-full-feedback/vllm
```

That command prints the path of a case-local evaluator.  Save the agent's
response using `candidate.schema.json`, then run:

```sh
/tmp/manual-full-feedback/vllm/vllm-005/evaluate_pcvs.sh response.json
```

The evaluator prints one JSON object containing the accepted candidate, full
Dr. Perf metrics, assessment, irregularity percentage, and strict pass/retry
decision.  For the next attempt, increment the response's `iteration` and call
the same case-local evaluator again.  The automated runner uses the same
`evaluate_pcvs.py` implementation.  A case whose native workload never reaches
the marker is recorded as `never-reached` with zero iterations and does not
stop the remainder of a suite.
