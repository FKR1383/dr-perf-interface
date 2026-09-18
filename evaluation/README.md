# Variable discovery evaluation

Compare two ways of finding which program-state variables determine the cost
of a marked region:

- **Agent Only with measurability feedback** reads the source and predicts the
  relevant variables. A separate instrumentation service can tell it why its
  answer cannot be measured, so it can revise that answer. It cannot run the
  program, profile it, edit files, or see performance feedback.
- **Agent + Dr. Perf** reads the source, chooses variables to try, instruments
  the region, and uses measurements to find a lower-irregularity model. It stops
  when any successful attempt is strictly below the target or the measurement
  budget is exhausted, then selects the lowest-irregularity successful attempt.

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

Both sides now submit measurements to **one harness-owned execution service**.
Every measurement starts a fresh process at the same workspace and raw-output
paths, using the environment captured before either agent runs. The service
copies the instrumented candidate, resets its temporary/cache directories, and
discards Python bytecode caches, including those created by an instrumenter.
The experimental helper submits a request; its shell environment does not
launch or configure the measured workload. The supplied workload, hash seed,
thread settings, measurement scope, and fitter are shared across both sides.
Only permitted instrumentation and necessary feature bindings may differ.

Each measurement saves `execution.json` with its actual command, paths,
environment fingerprint (without dumping the environment), scope, and input-file
hashes. `result.json` also records the common `measurement_protocol`.
These controls remove differences caused by the two launch routes; they do not
make time, OS scheduling, external mutable data, random inputs inside the
application, or instrumentation-induced runtime state deterministic. Use a
deterministic, self-contained workload. Separately built binaries must retain
the same compiler settings and use relocatable paths. Equal features should
be checked against raw counts, rather than assuming that labels alone prove
identical execution. Results from the old mixed-launcher protocol should be
rerun on both sides before comparison.

## Fixed workloads in every workspace

The **workload driver supplies inputs**; the target program computes its local
variables from them. Agents select expressions to observe, not assignments to
feed the workload. For example, `aq-001/tests/test_case.py` constructs enums at
fixed sizes and with fixed member values; `len(enum_class._member_map_)` observes
the dictionary while those enums are being constructed.

`evaluation/run.py` requires a frozen workload definition before invoking either
agent. Python benchmark exports supply it through `case.json`; their driver,
data, dependencies inside the workspace, and all source outside the target
marker's state keywords are protected automatically. This is based on the
export metadata, not on the benchmark ID. The command and its arguments are
fixed for the evaluation. Each measurement validates the protected files before
execution and afterward. Changed files, missing files, new auxiliary files, or
changed assignments outside instrumentation produce `invalid_measurement`,
with no usable formula or score. Details are saved in `workload-check.json`.
Target-region call counts and values of features shared with earlier successful
measurements are also compared in call order; mismatches are rejected. This
check does not reveal the static agent's answer or measurements to its competitor.

For a custom workspace, add `.drperf-workload.json` before evaluation:

```json
{
  "version": 1,
  "instrumentation": {
    "kernel.py": {"kind": "python-marker"}
  }
}
```

The `python-marker` rule compares Python syntax trees after removing only state
keywords from the existing `perfmark.region('target', ...)` call. It permits
feature expressions and formatting changes, while preserving assignments,
control flow, region boundaries, and the rest of the program. It requires
exactly one target marker per declared source file. Feature expressions must
be read-only; this is not a proof that arbitrary called functions have no side
effects. Bindings needing additional edits must be declared in advance.

For C/C++ or another language, explicitly bound the editable instrumentation
block with unique anchors, leaving the workload assignments outside it:

```json
{
  "version": 1,
  "instrumentation": {
    "driver.c": {
      "kind": "text-block",
      "start": "/* EVALUATION_STATES_BEGIN */",
      "end": "/* EVALUATION_STATES_END */"
    }
  },
  "build": ["./build.sh"],
  "build_outputs": ["program", "kernel.o"]
}
```

All text outside those anchors is frozen, including the driver assignments and
region body. Code inside must only bind read-only features and begin the marker.
The harness removes existing build outputs and rebuilds every candidate with
the same frozen command, environment, and working directory. Build scripts and
compiler settings stored in the workspace cannot change. Output entries are
exact relative paths; a trailing `/` allows a generated directory. Do not put
input data or source files under generated-output paths. Workload files must
be local to the snapshot; external dependencies must remain fixed separately.
The zlib and Rodinia preparation scripts now write these definitions. For an
older prepared workspace, add the definition with its existing state-block
anchors and build outputs, or prepare a fresh workspace.

Frozen source and files do not freeze fresh values obtained from clocks, live
services, operating-system randomness, or thread scheduling. Materialize such
**input data once** into workspace files before evaluation, then make the driver
read the same files on every call/run. Alternatively, use a deterministic input
generator with explicit fixed seeds in the supplied command. The harness does
not silently rewrite application randomness or manufacture assignments.

For stronger verification of actual input values (including array contents),
add `"input_trace": "workload-inputs.json"` to the definition. The frozen driver
must write that relative file as a nonempty JSON array containing complete input
records in call order, independently of the chosen performance features. The
harness removes any stale trace before each run, compares the newly recorded
values with the first measurement, and rejects missing/different traces. It
saves the trace beside each measurement. This protocol works with any language;
the driver must record the actual values it supplies, not just a seed, sizes,
case labels, or selected features. Without a full input trace, only frozen
files, source structure, call counts, and shared observed features are checked;
unobserved runtime values are not claimed to have been verified.

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

## Reproduce instruction-count differences without an agent

For the exported `aq-001` benchmark, run:

```sh
python3 evaluation/reproduce_aq001.py --workspace /tmp/aq-001
```

If needed, first export it with
`python3 benchmarks/regions/collect.py export aq-001 /tmp/aq-001`.
The reproducer copies the workspace and declares only
`len(enum_class._member_map_)`. It runs the unchanged workload four times, with
0, 16, 0, and 16 extra environment variables respectively. The added variables
are named `DRPERF_DIAGNOSTIC_UNUSED_0` through `DRPERF_DIAGNOSTIC_UNUSED_15`, each
set to `padding`; the benchmark does not use them. This deliberately changes
process environment while keeping the program inputs fixed. It requires a built
Dr. Perf and makes no Codex/API calls.

The same instrumented workspace and collector output path are used for each
run. Workspace bytecode caches are removed before every measurement. Source
and workload hashes must stay unchanged, and the complete ordered sequence of
recorded feature values must match before counts are compared. A run does not
silently pair calls with different inputs or average repeated feature values.

The terminal prints a sample of differing **raw instruction counts**, and the
retained output directory contains:

- `counts.csv`: every call's feature value and instruction count in each run.
- `comparison.json`: all per-call counts, formulas, irregularities, and checks.
- `setup.json`: workload command, instrumentation feature, hashes, and conditions.
- `run-NN-envN/`: each measurement's raw traces, block counts, and workload log.
- `workspace/`: the fixed instrumented copy, for inspection.

These are the trace's per-call `self` instruction counts, before marker-cost
calibration, not predictions from the fitted formula. Different environments
can change instruction counts; a particular score change is not guaranteed.
Matching counts are reported honestly. To repeat with no deliberate environment
change instead:

```sh
python3 evaluation/reproduce_aq001.py --workspace /tmp/aq-001 --env-counts 0 0 0 0
```

Use `--results-dir PATH` to choose a new or empty output directory. You can also
specify other conditions, for example `--env-counts 0 16 64 128`.

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
**ten measurements in the experimental search**, including failures and repeats.
The agent first measures a minimal candidate justified by source inspection.
Further changes must explain specific residual work; it may also test
simplifications, repair failures, or repeat a candidate to check stability.
All repeats remain in the report. After each measurement, the agent checks
whether any successful attempt is strictly below the target or the budget is
exhausted. Otherwise it must continue. A plausible explanation, a worse attempt,
or a preference for fewer features is not a stopping condition.

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

The harness verifies all recorded measurements and selects the successful
attempt with the lowest exact irregularity, even if the agent's reply selected
another attempt. Fewer features break exact score ties, followed by the earliest
attempt. Source reasoning guides candidate discovery; the measured score
determines the final choice. Every recorded attempt remains in the results.

If the agent returns above the target with budget remaining, the harness invokes
it again in the same disposable workspace with its prior measurements. Two
consecutive invocations that add no measurements stop the search with
`agent_stopped_without_progress`, an explicit failure to complete the search
contract rather than a successful early stop. Execution errors also end the run.

The terminal and `result.json` identify the selected and lowest-score attempts;
these are the same whenever a successful model exists. In `search`,
`selected_attempt` identifies the selected record and `best_attempt` identifies
the lowest-scoring successful record, or `null` if all measurements failed.
`target_met` describes the selected model. Normal `stop_reason` values are
`target_met` and `attempt_limit_reached`.

New results identify this search policy as `minimum_irregularity`. Runs labelled
`source_guided` allowed subjective early stopping and higher-score selections;
distinguish those results when comparing policies. Finishing above the target
saves the selected model and returns exit code **2**, including a stalled search.
Selecting a model below the target returns **0**. Missing experimental models and execution/contract errors
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
| `--target-irregularity F` | Stop when any successful attempt is strictly below F; otherwise continue to the measurement budget. Default: 0.10 (10%); use 0.05 for 5%. Valid range: greater than 0 and at most 1. |
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
copy. Each Codex invocation can run multiple experiments within the shared
measurement budget. Continuations use the same experimental workspace and prior
measurements; they never receive Agent Only's answer. Their logs are saved under
`logs/agent_drperf/continuation-NNN/`.
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
