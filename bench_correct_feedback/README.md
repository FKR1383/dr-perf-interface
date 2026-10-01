# Full-feedback PCV evaluation

This directory contains the reproducible evaluation in which one isolated
`agent_PCVs` thread selects PCVs for one case. A trusted deterministic script
validates the response, runs Dr. Perf, applies the strict `< 10%` success rule,
and returns the complete Dr. Perf report. There is no measurement agent.

Run every command below from the repository root:

```bash
cd /path/to/dr-perf-interface
```

Prerequisites are a working `codex` CLI login and a built Dr. Perf installation
for this checkout. Pin the selector model for repeatable trials instead of
depending on the CLI default:

```bash
export DRPERF_AGENT_MODEL=gpt-6-astra
```

The chosen value is recorded in each suite's `experiment-protocol.json` and
case isolation receipt. Use the same value for both feedback conditions.

## Suites

| Suite | Cases | Runner | Runtime requirement |
| --- | ---: | --- | --- |
| vLLM | 67 | `run_vllm.sh` | Included pinned vLLM CPU checkout and virtualenv |
| WAN | 41 | `run_wan.sh` | Pinned Diffusers checkout and its Python environment |
| Accidental quadratic | 21 | `run_accidental_quadratic.sh` | Current Python environment |
| Growth multifold | 2 | `run_growth_multifold.sh` | Current Python environment; specialized fixed workloads are staged |
| V8 interpreter | 50 | `run_v8_interpreter.sh` | Currently unavailable; recorded as `never-reached` |
| V8 regexp | 28 | `run_v8_regexp.sh` | Currently unavailable; recorded as `never-reached` |

The V8 source cases are present, but the repository has no pinned, rebuilt,
perfmark-linked `d8` adapter. The V8 runners therefore create honest blocked
reports without launching an agent. An arbitrary system `d8` would not contain
the candidate annotation and is not a valid substitute.

## Run or resume a suite

The runners are checkpointed and safe to resume. Each suite uses a file lock,
prints events to the terminal, and appends them to `SUITE/interactive-run.log`.

```bash
./bench_correct_feedback/run_vllm.sh
./bench_correct_feedback/run_accidental_quadratic.sh
./bench_correct_feedback/run_growth_multifold.sh
./bench_correct_feedback/run_v8_interpreter.sh
./bench_correct_feedback/run_v8_regexp.sh
```

WAN needs the exact pinned Diffusers source tree and Python environment:

```bash
./bench_correct_feedback/run_wan.sh \
  --runtime-template /path/to/pinned/diffusers \
  --python /path/to/wan-venv/bin/python
```

The generic entry point is equivalent:

```bash
./bench_correct_feedback/run_suite.sh accidental-quadratic
```

Run one case by adding `--case`:

```bash
./bench_correct_feedback/run_accidental_quadratic.sh --case aq-003
./bench_correct_feedback/run_vllm.sh --case vllm-005
```

## Observe without running

```bash
./bench_correct_feedback/status.sh vllm
./bench_correct_feedback/status.sh accidental-quadratic --all
./bench_correct_feedback/status.sh growth-multifold --json

./bench_correct_feedback/audit_isolation.sh vllm
./bench_correct_feedback/audit_isolation.sh accidental-quadratic
```

`status.sh` is read-only. `audit_isolation.sh` checks unique per-case threads,
disabled tools, absence of a measurement agent, fixed workload digests, and
thread/workload separation from the scalar experiment.

After running any number of suites, combine their reports with:

```bash
./bench_correct_feedback/report.sh
```

This writes `experiment-report.{json,md,csv}` without running a benchmark.

## Manually submit one agent response

Prepare a case without starting `agent_PCVs`:

```bash
python3 bench_correct_feedback/run_agent_pcvs.py accidental-quadratic \
  --case aq-003 --prepare-only --root /tmp/manual-full-feedback
```

Then save a response matching `candidate.schema.json` and evaluate it:

```bash
/tmp/manual-full-feedback/aq-003/evaluate_pcvs.sh response.json
```

The evaluator prints the complete machine-readable Dr. Perf result. The
case-local script is bound to that case's isolated controller state.

## Output structure

Each completed case contains:

```text
SUITE/CASE/
  case-actual/                         fixed clean source and workload
  agent_PCVs/PROMPT.md                 common selector instructions
  agent_PCVs/isolation.json            isolation receipt and thread identity
  agent_PCVs/turn-NNN-prompt.md         exact prompts sent to the selector
  iterations/iteration-NNN/
    annotation.diff                    annotation-only change
    candidate.json                     exact selected PCVs
    drperf-full-report.json            complete retained Dr. Perf report
    script-decision.json               deterministic validity/pass decision
    agent-visible-feedback.json        exact report shown to agent_PCVs
    workload-output.txt                workload output
  case-report.json
  case-report.md
  evaluate_pcvs.sh
```

Each suite also receives `full-report.json`, `full-report.md`, and
`full-report.csv`. Trusted mutable controller state stays under
`SUITE/.controller-runs/` and is not exposed to the tool-free selector.

Success requires valid irregularity strictly below `10%`, with at most ten
measured candidates and at most four PCVs per candidate.
