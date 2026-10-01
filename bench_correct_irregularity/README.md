# Scalar-irregularity PCV evaluation

This directory contains the controlled scalar-feedback evaluation. One fresh,
tool-free `agent_PCVs` thread is created for each case. A trusted deterministic
script—not a second agent—validates candidates, runs Dr. Perf, and applies the
strict `< 10%` decision.

Run commands from the repository root:

```bash
cd /path/to/dr-perf-interface
```

Prerequisites are a working `codex` CLI login and a built Dr. Perf installation
for this checkout. Pin the same selector model used by the full-feedback trial:

```bash
export DRPERF_AGENT_MODEL=gpt-6-astra
```

The value is recorded in `experiment-protocol.json` and each isolation receipt.

## Exactly what the selector sees

For a valid measurement, `agent_PCVs` receives only:

```json
{"irregularity_percent": 17.25}
```

For an invalid measurement, no irregularity exists. The selector receives
sanitized validity diagnostics instead:

```json
{
  "status": "invalid",
  "reasons": ["insufficient state points: 2; need 6"]
}
```

It never receives the fitted formula, coefficients, per-state values,
instruction counts, attribution, or irregularity breakdown. A PCV mismatch may
name expected or missing PCVs because that is validation feedback. Invalid
measured candidates still consume an iteration; infrastructure failures do not.

This is feedback schema `score-or-sanitized-invalid-v2`. The runner refuses to
mix it with an old run that represented every invalid measurement as `100%`.

## Suites and runners

| Suite | Cases | Runner | Runtime requirement |
| --- | ---: | --- | --- |
| vLLM | 67 | `run_vllm.sh` | Included pinned vLLM CPU checkout and virtualenv |
| WAN | 41 | `run_wan.sh` | Pinned Diffusers checkout and its Python environment |
| Accidental quadratic | 21 | `run_accidental_quadratic.sh` | Current Python environment |
| Growth multifold | 2 | `run_growth_multifold.sh` | Current Python environment; specialized fixed workloads are staged |
| V8 interpreter | 50 | `run_v8_interpreter.sh` | Blocked: no pinned instrumented `d8` adapter |
| V8 regexp | 28 | `run_v8_regexp.sh` | Blocked: no pinned instrumented `d8` adapter |

V8 runners write `never-reached` reports and do not spend agent tokens.

## Start or resume

```bash
./bench_correct_irregularity/run_accidental_quadratic.sh
./bench_correct_irregularity/run_growth_multifold.sh
./bench_correct_irregularity/run_v8_interpreter.sh
./bench_correct_irregularity/run_v8_regexp.sh
```

WAN requires explicit pinned runtime paths:

```bash
./bench_correct_irregularity/run_wan.sh \
  --runtime-template /path/to/pinned/diffusers \
  --python /path/to/wan-venv/bin/python
```

Start or resume the vLLM scalar-feedback experiment in its canonical root:

```bash
./bench_correct_irregularity/run_vllm.sh
```

Run one case with `--case`:

```bash
./bench_correct_irregularity/run_accidental_quadratic.sh --case aq-003
```

## Status and isolation audit

```bash
./bench_correct_irregularity/status.sh accidental-quadratic
./bench_correct_irregularity/status.sh growth-multifold --all
./bench_correct_irregularity/audit_isolation.sh accidental-quadratic
```

The audit verifies disabled tools, unique per-case threads, absence of a
measurement agent, allowed scalar feedback shapes, and separation from the
full-feedback experiment.

Combine every available suite report without running benchmarks:

```bash
./bench_correct_irregularity/report.sh
```

This writes `experiment-report.{json,md,csv}`.

## Manual JSON-in evaluation

```bash
python3 bench_correct_irregularity/run_agent_pcvs.py accidental-quadratic \
  --case aq-003 --prepare-only --root /tmp/manual-scalar
/tmp/manual-scalar/aq-003/evaluate_pcvs.sh response.json
```

The evaluator returns the complete report to the human caller. Only the
sanitized `agent-visible-feedback.json` enters the next agent prompt.

## Output and reports

Each case has the same structure as the full-feedback experiment:

```text
SUITE/CASE/
  case-actual/
  agent_PCVs/{PROMPT.md,isolation.json,turn-NNN-prompt.md,events/}
  iterations/iteration-NNN/
    annotation.diff
    candidate.json
    drperf-full-report.json
    script-decision.json
    agent-visible-feedback.json
    workload-output.txt
  case-report.{json,md}
  evaluate_pcvs.sh
```

Complete reports are retained outside the isolated agent directory. Suite
aggregates are written as `full-report.json`, `full-report.md`, and
`full-report.csv`.

Every retained `drperf-full-report.json` includes `irregularity_breakdown`,
with complete function-level attribution of non-affine instructions. This
breakdown remains private to the trusted evaluator: `agent_PCVs` still receives
only the scalar percentage or sanitized invalid-measurement diagnostics.
