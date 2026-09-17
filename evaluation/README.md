# Variable discovery evaluation

Compare two ways of finding which program-state variables determine the cost
of a marked region:

- **Agent Only** reads the source and predicts the relevant variables. It cannot
  run the program, profile it, or edit files.
- **Agent + Dr. Perf** reads the source, chooses variables to try, instruments
  the region, and keeps using measurements to revise its answer until it finds
  a formula below the irregularity target or uses its experiment budget.

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
The earlier [zlib compression case study](case_studies/zlib/README.md) includes
fixed file workloads and a separate validation step.

The workload must reach the region and vary its state enough to fit a model.
Dr. Perf supports up to four declared integer states and needs at least
`max(3, number of states + 2)` distinct state combinations. The harness uses
your supplied workload; it does not generate one.

## Read the results

The terminal shows Agent Only's predicted variables, followed by each
Agent + Dr. Perf attempt and its final selection. Each attempt includes:

- **Variables:** the candidate set the agent measured.
- **Formula:** the fitted instruction cost per call, excluding nested marked
  regions.
- **Irregularity:** the share of cost that the declared states do not explain.
  Lower values mean less unexplained cost in that run.
- **Status:** whether the measurement produced a model, or why it failed.

The default target is **strictly below 10% irregularity**, with a hard limit of
**ten measurements per evaluation**, including failures. The agent must keep
testing new candidate sets while the target is unmet and attempts remain.
Worse attempts guide further investigation;
they do not justify stopping. Successfully measured sets cannot be repeated,
but failed measurements can be repaired and retried.

Use `--max-attempts 5` for a smaller search and `--target-irregularity 0.05` for
a target below 5%. Budgets above ten are rejected. This limits measurements,
not elapsed time. The target uses a fraction, not a percentage. Exactly the
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
target returns **0**. Missing models and execution/contract errors return **1**.

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

Measurement details also list up to five functions contributing the most
unexplained cost, with their shares of total cost. These guide source inspection
for the next candidate. Calls with identical declared states are averaged, and
the current fitter only splits one-variable models into regimes. Meeting the
target describes the measured fit; it does not prove per-call accuracy or
identify a unique correct variable set.

## Options

Place optional flags before `--`:

| Option | Purpose |
| --- | --- |
| `--max-attempts N` | Limit the Dr. Perf agent to N measurements, including failures. Default and maximum: 10; smaller budgets are allowed. |
| `--target-irregularity F` | Stop strictly below fraction F. Default: 0.10 (10%); use 0.05 for 5%. Valid range: greater than 0 and at most 1. |
| `--model NAME` | Choose a Codex model. Default: your normal Codex configuration. |
| `--results-dir PATH` | Save results in a new or empty directory. `evaluation/results/` is gitignored. |
| `--ground-truth n,entries` | Compare each agent's answer with this set of variables. |

Ground-truth comparison reports exact set equality, missing variables, and extra
variables. Use `--ground-truth ''` for the empty set. If omitted, the harness
simply reports both answers. Neither agent receives the ground truth.

## Isolation

The agents run in separate, fresh Codex sessions on separate copies of the same
source, including uncommitted changes. Agent Only runs first in a read-only
sandbox. Its session files are removed before Agent + Dr. Perf starts, and its
results are held until both runs finish.

Agent + Dr. Perf makes instrumentation edits and rebuilds only in its disposable
copy. Any continuation uses a fresh Codex invocation with that same experimental
workspace and its own prior measurements; it never receives Agent Only's answer.
Continuation logs are saved under `logs/agent_drperf/continuation-NNN/`.
It is instructed not to optimize or change the program's behavior. The
copies are discarded after evaluation; your original source is left intact.

## Tests

The tests substitute Codex calls and do not use the Codex API:

```sh
python3 -m unittest discover -s evaluation/tests -v
```

To also compile and measure the existing C affine example with a built Dr. Perf:

```sh
DRPERF_EVAL_INTEGRATION=1 python3 -m unittest discover -s evaluation/tests -v
```
