# Agent PCV discovery benchmark

The question: **within a few measurement rounds, how accurately can an agent
identify a program region's performance-critical variables, with and without
drperf feedback?** Coefficients are inferred by the checker. Optimization is a
separate task and is not the score here.

A second question is whether **symbolic insights from small inputs reduce the
need for long or large benchmark runs**. The [small-to-large track](SMALL_TO_LARGE.md)
restricts agent measurements to small inputs and tests frozen predictions on
larger evaluator-only inputs. Its SQLGlot pilot enforces an input-size envelope;
large-input validation and compute-savings results are still pending.

The target is 200–1,000 distinct code regions or behaviors. The initial import
contains **29 documented case families**, including the slide deck's 8 FTL,
9 vLLM and 4 Wan cases, plus 8 later systems cases. An additional inventory
contains **201 historical region-name candidates** from 151 measurement reports.
These counts are not additive: the region inventory overlaps the case families.
Candidates are not validated benchmark cases, and workload sizes are not
counted as independent cases.

Three reviewed neutral workload adapters are available initially: `sqlglot`,
`vllm_b`, and `wan_a`. Remaining families preserve evidence and task descriptions
but need clean-source adapters and reviewed ground truth. There are no agent
accuracy results yet.

## Paired protocol

For each case and agent seed, start two fresh sessions with identical model,
prompt, source revision, dependencies, fixtures, CPU/GPU resources and budgets:

| Condition | Available measurement feedback |
| --- | --- |
| `timing` | Wall time and time-based function profiling (`cProfile` in the pilots) |
| `drperf` | The same timing tools, plus region instruction counts, inferred affine formulas and unexplained-cost attribution |

Both agents may inspect source, change inputs, and add observation code. The
drperf agent chooses its annotations; solved PCVs are never preinstalled.
Neither agent may optimize the workload during discovery. Record the code-only
answer as round 0, then record the updated answer after every measurement.

Default budget: **3 adaptive rounds, at most 6 input configurations per round**.
Each configuration launches one workload process. This means at most 18
process launches, not literally three executions. A round selects timing *or*
drperf; requesting extra native timings uses another round. Fix the number of
internal calls/repetitions and the input-size envelope per case before an
evaluation. The pilot drivers have different internal loops, so launch count
alone is not a cross-case compute budget. Report launches, internal calls,
agent tokens, elapsed time, errors, and timeouts alongside accuracy.

Use the same budget for both conditions and report accuracy after rounds
0, 1, 2 and 3. The full drperf workflow is the treatment here, including
annotation effort; a more narrowly controlled feedback-only ablation can share
neutral region boundaries and a profiling API in a later protocol.

## What counts as correct

A submission contains claims with a source region, a PCV expression, evidence,
and its supported domain. PCVs use the program's language and may contain
products, conditionals, cardinalities, and other state computations. The cost
formula remains affine in the PCVs. A coefficient need not be supplied.

Evaluate semantic dependencies, not spelling. For example, `n*m` and `m*n`
describe the same PCV. A correlated proxy is not sufficient if an independent
input change separates it from the actual work. A hotspot name alone is not a
PCV. A supported constant-cost or zero-effect finding is a useful answer.

For each claim, review:

- Does it identify the correct region and explain the relevant dependency?
- Is its expression available at region entry, with the correct branch or loop
  regime? Can it be evaluated without changing behavior?
- Does it survive reserved input changes that separate alternative explanations?
- Is computing it appreciably simpler than re-executing the region? Record its
  computational cost; an oracle that runs the workload is disallowed.
- Does the evidence support its scope? Instruction count and wall time are
  different quantities, and a small observed fit is not an all-input proof.

The current scorer consumes **explicit evaluator judgments**, then calculates
precision, factor recall, F1, strict case accuracy, and the paired accuracy
difference. Strict accuracy requires all reviewed factors and no unsupported
claims. Also report first correct round and whether a once-correct answer was
later lost. This scoring is automatic; semantic grading is not yet automatic.
Human reviewers should receive anonymized submissions without the condition
label and reconcile disagreements. Historical marker lists are hypotheses,
not automatically correct answer keys.

For a validated release, each case also needs executable reference PCVs and
held-out fixtures. Evaluate agent expressions on those states, infer coefficients
on the training states, freeze them, and measure unexplained cost on held-out
states. Do not re-fit on held-out states or demand the archived coefficient.
This coverage metric supplements semantic accuracy: alternate affine bases can
explain the same cost, and explanatory fit alone does not establish causality.
The current archive import does not claim to implement that held-out execution
or to certify the provisional answer keys.

## Run the pilots

These commands use existing local dependencies and cached model weights. They
perform no downloads, apply no fixes, and do not modify the archived sources.
Source is exported from a pinned Git revision, not copied from marked working
trees. vLLM additionally needs ABI-compatible native libraries from that checkout.

```sh
python3 benchmarks/bench.py list
python3 benchmarks/bench.py prepare sqlglot /tmp/sqlglot-timing \
  --archive /home/ubuntu/drperf-cases --condition timing
python3 benchmarks/bench.py prepare sqlglot /tmp/sqlglot-drperf \
  --archive /home/ubuntu/drperf-cases --condition drperf

python3 benchmarks/bench.py submit /tmp/sqlglot-timing
python3 benchmarks/bench.py measure /tmp/sqlglot-timing --mode timing
```

Each workspace contains `TASK.md`, clean `source/`, `workload.py`, a default
`plan.json`, and `hypothesis.json`. The agent edits the plan and hypotheses.
Record `submit` before the first measurement (round 0), update the claims after
each measurement, and call `submit` again. Recorded answers cannot be overwritten
through the CLI. Measurement-only smoke runs can omit submissions, but those
runs cannot be scored as complete agent sessions.
For drperf, it also adds its own `perfmark.region(...)` annotations to the
workload or source, then requests:

```sh
python3 benchmarks/bench.py measure /tmp/sqlglot-drperf --mode drperf
```

Replace `sqlglot` with `wan_a` or `vllm_b` to prepare those pilots. Wan uses tiny
random weights on CPU; it measures real diffusers host paths but does not stand
in for GPU kernel latency. vLLM uses the CPU backend and cached OPT-125M weights.
The small pilot plans are smoke inputs, not finalized discovery/held-out splits.

The supervisor records pre-run hypotheses, source hashes, input plans, process
outcomes, raw profiles, and validity warnings. drperf feedback merges compatible
basic-block observations across the round's processes; it does not infer
cross-process temporal relations. Invalid counts suppress formulas. Failed
rounds consume budget. `cProfile` perturbs execution and includes startup; use
its function breakdown and report initialization separately. Timings under
drperf are instrumented timings and must not be compared to native latency.

`bench.py` is a supervisor, **not an isolation sandbox**. In a real evaluation,
run agents in separate containers with only their prepared workspace, permitted
tool runtime and dependencies. Keep `session.json`, measurement logs and the
budget ledger under supervisor control. Do not mount this repository, the
archive, Git history, answer keys, or sibling sessions into the agent container.
The pilot adapter exports task files separately but shared-filesystem execution
cannot prevent an agent from reading evaluator answers or changing its budget.

## Case layout and scaling

```text
cases/<id>/case.json                 public identity and readiness
cases/<id>/task.md                   neutral task
cases/<id>/reference/record.md       original case narrative (evaluator only)
cases/<id>/reference/answer.json     provisional semantic factors
cases/<id>/reference/provenance.json source paths, lines and hashes
cases/<id>/reference/assets/         historical drivers, annotations and fixes
evaluator/evidence/                  full record, slide deck and deck builder
evaluator/region-candidates.json     region-level expansion queue
evaluator/region-reports/            measurement evidence for that queue
```

To reach 200–1,000, promote distinct source regions from the candidate queue
after removing aliases, empty probes, fixed variants and invalid runs. Add
cases from additional codebases once that pool is exhausted. Retain cases with
linear, product, staircase, branch-dependent, history-dependent and constant
costs, including negative findings and measurement artifacts. Do not select
only regions for which drperf already found an excellent fit.

Split by source/behavior family before tuning prompts. All variants of one
underlying dependency belong to the same split and statistical cluster. Report
unique regions and systems separately from seeds and workload variants. Publish
family-balanced results as well as pooled accuracy; report infrastructure
failures rather than silently dropping difficult cases.

Re-import or extend the evidence without running historical scripts:

```sh
python3 benchmarks/tools/import_archive.py /home/ubuntu/drperf-cases
python3 benchmarks/tools/inventory_regions.py /home/ubuntu/drperf-cases
python3 -m unittest discover -s benchmarks/tests -v
python3 benchmarks/evaluator/score.py reviewed-sessions.json --output scores.json
```

See [the judgment format](evaluator/JUDGMENTS.md) for the evaluator input.
