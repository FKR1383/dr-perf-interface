# Variable discovery evaluation

Compare two ways of finding which program-state variables determine the cost
of a marked region:

- **Agent Only with measurability feedback** reads the source and predicts the
  relevant variables. A separate instrumentation service can tell it why its
  answer cannot be measured, so it can revise that answer. It cannot run the
  program, profile it, edit files, or see performance feedback.
- **Agent + Dr. Perf** reads the source, chooses variables to try, instruments
  the region, and keeps using measurements to revise its answer until it finds
  a formula below the irregularity target or uses its experiment budget.

The baseline runs first as a bounded loop: static proposal, separate
instrumentation check, and a harness-controlled Dr. Perf measurement if the
candidate can be instrumented. Unsupported candidates receive a reason and
advice about representation, types, entry-state access, or binding requirements.
The static author chooses its own revisions in a fresh read-only invocation.
Formulas, irregularity, costs, traces, and performance diagnostics are never
sent back. The loop stops on the **first measurable set, regardless of its
irregularity**, or at its round limit. Agent + Dr. Perf then runs independently.

Baseline revision invocations append only the prior proposals and measurability
feedback to the initial static prompt.
This baseline is explicitly labelled as static reasoning with measurability
feedback; its initial unassisted answer is preserved separately.

Both agents return source-level names or expressions, such as `n` or
`len(queue)`. The agent chooses the variables; the harness runs the evaluation
and records the results. Ground truth is optional.

## Run an evaluation

You need Python 3.8+, a built Dr. Perf (`./build.sh`), and an authenticated
Codex CLI available as `codex`. The CLI must support `exec --ephemeral`,
`--output-schema`, and `--output-last-message`.

From the Dr. Perf repository root, run:

```sh
python3 evaluation/run.py \
  --workspace /path/to/project \
  --region parse \
  -- python3 app.py
```

- `--workspace` is the project directory containing the target source.
- `--region` is the name of an existing perfmark region in that project.
- Everything after `--` is the normal command used to exercise the program.
  For a compiled program, this could be `-- ./program arg1 arg2`.

The workload runs from a temporary copy of the workspace. Include the files
needed to run and, for compiled programs, rebuild the target. Use relative paths
in scripts and build configuration so they work in the copy. Git metadata is
not copied.

For a CPU machine-learning example with generated numeric inputs, see the
[Rodinia Backpropagation case study](case_studies/rodinia_backprop/README.md).
The [Rodinia k-means case study](case_studies/rodinia_kmeans/README.md) measures
clustering through convergence and tests data-dependent work using generated
points, including different coordinate sets with the same dimensions.
The earlier [zlib compression case study](case_studies/zlib/README.md) includes
fixed file workloads and a separate validation step.

The workload must reach the region and vary its state enough to fit a model.
Dr. Perf has no fixed limit on the number of declared integer states. A fit needs
at least `max(3, number of states + 2)` distinct state combinations. The collector
retains at most 128 combinations per region, subject to its counter-memory
budget; exceeding those limits invalidates the measurement. More features still
require enough varied inputs. The harness uses your supplied workload; it does
not generate one.

## Read the results

The terminal shows Agent Only's predicted variables, followed by each
Agent + Dr. Perf attempt and its final selection. Each attempt includes:

- **Variables:** the candidate set the agent measured.
- **Formula:** the fitted instruction cost per call, excluding nested marked
  regions.
- **Irregularity:** the share of cost that the declared states do not explain.
  Lower values mean less unexplained cost in that run.
- **Status:** whether the measurement produced a model, or why it failed.

Agent Only's section shows its initial variables when revised, final variables,
measurability rounds and stopping reason, plus the final formula, irregularity,
and measurement status computed by the same Dr. Perf adapter. These scores are
visible to the user, not the static author. Files and matching `result.json` keys:

- `agent_only_initial.json`: the first, unassisted variable-only answer.
- `agent_only.json`: the final variable-only answer after measurability checks.
- `agent_only_measurability.json`: every proposal and its sanitized feedback,
  round budget, and stopping reason.
- `agent_only_measurement.json`: the final candidate's measurement, or failure.

Both competitors may propose any number of features. If a candidate has labels
too long for Dr. Perf or cannot be faithfully exposed as integer entry state,
the service reports that limitation. The author can revise its proposal; the
harness never drops or substitutes features for
it. Each candidate stays frozen while it is being checked. If the loop exhausts
its budget, formula and score remain `null` (`n/a`) with a reason. An execution
or tool failure ends the loop without treating it as evidence about cost
dependencies. The empty answer remains valid for discovery, but Dr. Perf cannot
currently fit it.

The default target is **strictly below 10% irregularity**, with a hard limit of
**ten measurements in the experimental search**, including failures. The agent must keep
testing new candidate sets while the target is unmet and attempts remain.
Worse attempts guide further investigation;
they do not justify stopping. Successfully measured sets cannot be repeated,
but failed measurements can be repaired and retried.

Use `--max-attempts 5` for a smaller search and `--target-irregularity 0.05` for
a target below 5%. Budgets above ten are rejected. This limits search measurements,
not elapsed time. The baseline has a separate `--agent-only-max-rounds` budget:
**3 rounds by default, maximum 10**, counting the initial proposal. Each round
uses a fresh static invocation and at most one instrumentation invocation and
one workload measurement. It does not consume the experimental search budget
and never retries to improve an irregularity score. Use one round for an
unassisted static answer followed by a single measurability check.
The target uses a fraction, not a percentage. Exactly the
threshold does not meet it. A measurement with `status: ok` can still be above
the target.

The harness checks the recorded measurements. If the agent returns early above
the target, it invokes the experimental agent again with its previous answer,
the existing workspace, and the remaining measurement budget. Two consecutive
continuations that add no measurements end with an explicit unresolved result
to prevent unlimited retries. Every recorded attempt remains in the results.

The report selects the lowest-irregularity successful measurement, preferring
fewer states for a tie and then the earliest attempt. This ranking uses verified
measurements even if the agent's final reply selects a worse attempt. Original
agent replies remain in the logs. The terminal and `result.json` report the
best attempt, target, whether it was met, attempts used, and the stopping reason.
Reaching the budget above the
target saves the selected model and returns exit code **2**; reaching the
target returns **0**. Missing experimental models and execution/contract errors
return **1**. An unavailable baseline measurement is reported without discarding
the experimental result or changing these exit codes.

Failed measurements have `null` formula and irregularity in JSON, displayed
as `n/a` in the terminal. A measured irregularity of zero is a successful
result with no unexplained cost. An empty variable set is a valid answer,
although Dr. Perf currently cannot fit a model with no declared states. If no
model is selected, the harness saves the results and exits with a nonzero status.

The results directory is printed at the end. It contains `result.json` with
both answers, separate `agent_only.json` and `agent_drperf.json` files, and
`logs/` and `measurements/` for inspection. JSON stores irregularity as an exact
fraction, such as `0.021`; the terminal displays it as a percentage, `2.1%`.
By default, results are saved in a temporary directory that remains after the run.

Baseline raw data, feature-to-code bindings, and instrumentation patches are
saved under `measurements/agent_only/round-NNN/`. Static and instrumentation logs
are under `logs/agent_only/round-NNN/` and
`logs/agent_only_instrumentation/round-NNN/`. Inspect those bindings when reviewing
how complex expressions or library state were exposed. Round progress and
measurability statuses are printed while the baseline loop is running.

Measurement details also list up to five functions contributing the most
unexplained cost, with their shares of total cost. These guide source inspection
for the next candidate. Calls with identical declared states are averaged, and
the current fitter only splits one-variable models into regimes. Meeting the
target describes the measured fit; it does not prove per-call accuracy or
identify a unique correct variable set.

Both competitors use the same checked-out Dr. Perf engine and measurement scope.
The fitter accepts valid negative intercepts, such as `a*(depth-1)`; a negative
constant alone is not evidence of curvature. Results from the earlier fitter,
which rejected sufficiently negative intercepts, are not directly comparable.
Rebuild after updating the engine, record the revision with your results, and
rerun both competitors when comparing versions. Keep `DRPERF_EXCLUDE_CUDA_MODULE`
and `DRPERF_FOLLOW_THREADS` identical across compared runs; these optional controls
change which instructions are counted. Their effective scope is recorded in the
raw Dr. Perf output.

The [source-region collection](../benchmarks/README.md) supplies targets for
discovery. Its [pilot protocol](../benchmarks/PIPELINE_DESIGN.md) compares timing
feedback with timing plus Dr. Perf and permits input changes. This harness uses
the fixed supplied workload and a static baseline with measurability feedback;
these are separate evaluation protocols, and their scores should not be pooled.

## Options

Place optional flags before `--`:

| Option | Purpose |
| --- | --- |
| `--max-attempts N` | Limit the Dr. Perf agent to N measurements, including failures. Default and maximum: 10; smaller budgets are allowed. |
| `--agent-only-max-rounds N` | Limit static proposal/measurability rounds, including the initial proposal. Default: 3; range: 1–10. Stops at the first measurable set, whatever its score. |
| `--target-irregularity F` | Stop strictly below fraction F. Default: 0.10 (10%); use 0.05 for 5%. Valid range: greater than 0 and at most 1. |
| `--model NAME` | Choose a Codex model. Default: your normal Codex configuration. |
| `--results-dir PATH` | Save results in a new or empty directory. `evaluation/results/` is gitignored. |
| `--ground-truth n,entries` | Compare each agent's answer with this set of variables. |

Ground-truth comparison reports exact set equality, missing variables, and extra
variables for the final selections. Use `--ground-truth ''` for the empty set. If omitted, the harness
simply reports both answers. Neither agent receives the ground truth.

## Isolation

The agents run in separate, fresh Codex sessions on copies of the same source
snapshot, including uncommitted changes. Every static proposal runs in a
read-only sandbox. Its session is deleted before a separate writable copy is
prepared for instrumentation. That instrumenter exits before Dr. Perf runs.
The measurement copy and its session are deleted before any static revision.
Raw artifacts remain in harness memory; they are not placed in the next copy.

Revisions receive only the author's previous proposals and an allowlisted
feasibility status/reason/advice. Free-text advice comes only from the
instrumenter before any measurement; native measurement failures are mapped to
fixed feasibility messages. Formulas, scores, instruction counts, traces, and
unexplained-function details are excluded. Each round starts from the original
source snapshot, not earlier instrumentation edits.

Agent + Dr. Perf makes instrumentation edits and rebuilds only in its disposable
copy. Any continuation uses a fresh Codex invocation with that same experimental
workspace and its own prior measurements; it never receives Agent Only's answer.
Continuation logs are saved under `logs/agent_drperf/continuation-NNN/`.
It is instructed not to optimize or change the program's behavior. The
copies are discarded after evaluation; your original source is left intact.

All baseline sessions finish before Agent + Dr. Perf starts. Baseline answers,
logs, measurements, and feedback remain unpublished until both competitors
finish, so the experimental agent receives none of them. The baseline loop
does not change the experimental agent's prompt, search policy, or budget.

## Tests

The tests substitute Codex calls and do not use the Codex API:

```sh
python3 -m unittest discover -s evaluation/tests -v
```

To also compile and measure the existing C affine example with a built Dr. Perf:

```sh
DRPERF_EVAL_INTEGRATION=1 python3 -m unittest discover -s evaluation/tests -v
```
