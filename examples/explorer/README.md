# Interactive region models

This measured producer/consumer program demonstrates a use of drperf above an
individual performance interface: perturb a producer PCV, propagate selected
state relationships, and inspect each affected region separately. There is no
sum of region costs and no prediction of elapsed time or parallel speedup.

`pipeline.c` runs two threads. The producer emits one to three batches per
round; the consumer drains them and runs decode, copy, lookup, and dispatch
regions. The queue relationship needs cumulative history, while the later
regions use the latest preceding values. The workload has 24 rounds and 169
marked calls, including startup.

## Open the measured example

Install [the VS Code extension](../../extensions/vscode/README.md), then run
**drperf: Open Producer/Consumer Demo**. In **What-if**, multiply `enqueue.items`
by two and explicitly select relationship assumptions. Inspect an affected
call to see the history values used to compute its new PCVs.

The extension includes the actual baseline, changed, refined, refined-changed,
expansion-changed, and joint-changed reports in `extensions/vscode/demo/`. The changed reports were
obtained by executing the program again, not generated from the predictions.
Use **Compare against a new measured report** to open `changed.drperf.json`.

## What the experiment finds

Doubling the producer workload correctly predicts every downstream PCV in this
example. Dequeue, decode, and copy cost predictions match their changed-run
measurements to floating-point precision. Enqueue includes mutex operations;
its changed-run instruction cost differs by about 0.02%, illustrating small
path variation that the checker's tolerance accepts. The bundled older reports
have no startup formula because their exporter required more varied states.
Re-exporting the raw capture with the current fitter gives a constant for its
single observed state, without claiming constant cost at other inputs.

The initial lookup annotation declares `entries`, but the body performs work
proportional to `entries * entries`. Some of its cost remains unexplained; a
line accepted over a narrow range also gives a **22.26% aggregate absolute
relative error** on the 16 changed calls whose formulas have no unexplained
blocks. The other eight calls are explicitly not checked. This is a negative
control: acceptance on small observed states does not prove extrapolation.

The refined annotation declares the semantic pair count:

```c
perfmark_begin("lookup", "pairs", items * items);
consumer_sink += work(items * items * 32);
perfmark_end("lookup");
```

The body is unchanged. drperf finds `128*pairs + 22` instructions/call, with no
unexplained blocks in this build. In **drperf: Open Refined PCV Demo**, propose:

```text
lookup.pairs = last("dequeue", "items") ** 2
```

The expression editor takes just the right-hand side. The checker verifies it
at all 24 recorded target calls; choosing it as an assumption lets the producer
change reach lookup. Comparing with `refined-changed.drperf.json` matches all
24 PCVs and all 24 measured lookup costs to floating-point precision.

Dispatch deliberately retains a branch boundary that the observations do not
locate exactly. Seven changed calls fall in the gap between fitted regimes and
remain unknown. The explorer does not silently extend one branch into that gap.
The measured numbers above depend on the checked-in x86-64 build and report;
regenerating with another compiler can change coefficients and constants.

## Reproduce and use from a terminal

Build drperf with `./build.sh`, then:

```sh
examples/explorer/verify.sh
```

This executes the six pipeline workloads and two call-structure controls,
exports their models, validates the scenarios, and writes results under
`out/explorer-validation/`. The raw sidecars are temporary and removed after
each export. No GPU is used.

To explore the bundled measurements without running DynamoRIO:

```sh
bin/drperf-explore extensions/vscode/demo/refined.drperf.json \
  --edit enqueue items scale 2 --assume-first \
  --propose lookup pairs 'last("dequeue", "items") ** 2' \
  --validate extensions/vscode/demo/refined-changed.drperf.json \
  -o out/refined-scenario.json
```

`--assume-first` is an explicit exploratory choice, not an inference of
causality. Use `--list` to inspect the available equations and `--relation ID`
to choose individual assumptions. Multiple `--edit` options change multiple
PCVs; `--scenario FILE` reloads a saved scenario tied to its source model.

## Distinguish relationships with a real intervention

The baseline supports two equations for copy's PCV:

```text
copy.bytes = 8 * last(decode.tokens)
copy.bytes = 16 * last(dequeue.items)
```

The `expansion-changed.drperf.json` run changes decode's expansion factor from
2 to 4 while keeping the producer batches unchanged. Enable **Compare
alternative relationships** after multiplying `decode.tokens` by two. The
candidate equations disagree, suggesting this small test can distinguish them.
The actual changed run follows the first copy equation.

The same intervention exposes a less obvious accidental relationship: the
first discovered equation for dispatch links its item count to copy's bytes.
That predicts the wrong dispatch PCV on all 24 calls, even though the equation
held at every original call. Proposing `dispatch.items = last(dequeue.items)`
passes the original-trace check and correctly predicts all 24 changed calls.
With that choice and the squared lookup PCV, all non-startup region costs match
the bundled expansion-changed measurements to floating-point precision. New
runs can retain the small mutex-path variation described above.

This illustrates an interactive loop above the region interfaces: keep several
observationally equivalent explanations, find an intervention where they
predict different states, run that small case, and retain the explanation that
survives. A successful test supports that intervention; it does not establish a
universal causal model or predict changed scheduling and call structure.

The explorer can now propose this experiment itself. Select relationship
assumptions and click **Find distinguishing experiments**, or run:

```sh
bin/drperf-explore extensions/vscode/demo/refined.drperf.json \
  --assume-first --suggest-experiments -o out/experiments.json
```

In the bundled refined report, the bounded search tries eight probes and
suggests multiplying `decode.tokens` by two. Its independently measured outcome
is the expansion-changed report above. Some other probes cannot be replayed:
adding one token makes the selected `dispatch.items = copy.bytes/16` relationship
produce a fractional state. The tool records that conflict rather than rounding
or treating it as evidence that the program cannot run.

## Compose two input changes, keeping every region separate

**drperf: Open Joint-Change Demo** loads this scenario, its explicit assumptions,
and the changed measured report together in VS Code.

The `joint-changed.drperf.json` measurement doubles producer batch sizes and
changes decode's expansion factor from two to three. The corresponding scenario
uses both `enqueue.items *= 2` and `decode.tokens *= 1.5`, with the squared lookup
and item-based dispatch relationships checked above. Every recorded PCV is
predicted correctly. Cost predictions match all calls of enqueue, dequeue,
decode, copy, and lookup to floating-point precision in this saved run. Dispatch
matches at its 17 supported calls; seven remain in the unknown regime gap.

This also gives a concrete abstract model. Let `s` be the producer multiplier,
`t` the decode expansion factor, `b` a producer call's original batch size, and
`q` a consumer round's original dequeued item count. Substitution through the
selected state equations gives these **conditional** per-call descriptions:

| Region | PCV after the change | Own instructions per call |
| --- | --- | --- |
| enqueue | `items = s*b` | `64*s*b + 91` |
| dequeue | `items = s*q` | `128*s*q + 19` |
| decode | `tokens = s*t*q` | `256*s*t*q + 23` |
| copy | `bytes = 8*s*t*q` | `256*s*t*q + 19` |
| lookup | `pairs = (s*q)^2` | `128*(s*q)^2 + 22` |

Each local cost interface remains affine in its declared PCVs, while their
composition can describe nonlinear responses to input changes. At `s=2, t=3`,
the variable-dependent work grows by factors of two, three, and four in different
regions; the constants remain. These rows are never added together. The algebra
uses chosen relationships and a fixed call structure, and the measured joint
case supports that one intervention, not every possible `s,t`.

```sh
bin/drperf-explore extensions/vscode/demo/refined.drperf.json \
  --edit enqueue items scale 2 --edit decode tokens scale 1.5 --assume-first \
  --propose lookup pairs 'last("dequeue", "items") ** 2' \
  --propose dispatch items 'last("dequeue", "items")' \
  --validate extensions/vscode/demo/joint-changed.drperf.json
```

## When the call structure changes

`call_structure.c` is a measured negative control. Doubling `batch.items`
increases the number of `item` calls from 36 to 72 while retaining eight batch
calls. Fixed-trace scenario validation rejects this changed structure instead
of aligning unrelated calls. **Compare runs** can still compare the seven shared
`item.bytes` states; their recorded per-call instruction costs are unchanged.
The control uses recorded counts to compare the raw instruction measurements
independently of marker-removal estimates. It is included in `verify.sh`.

State equations can still be rechecked despite that changed structure. The
proposal `batch.items = count("batch") + 1` holds on all eight original calls
but fails on all eight changed calls. `--check-relations` reports those actual
counterexamples without requiring a fixed marker sequence.

This distinguishes two questions: whether an existing region's interface has
changed, and whether a fixed recorded execution can predict a new run. The
former remains useful even when the latter is inapplicable.

## Scale check on an existing vLLM report

The viewer was also exercised on existing vLLM/ditto measurements, without a
new GPU run: 104 PCV-schema interfaces, 101 observed relationships, and 14,792
region calls. The original 103 region names include `rt.query` with two PCV
schemas, which the exporter keeps separate. With local source mapping and
bounded relationship discovery, export took about 47 seconds on the development
host. A tested single-PCV scenario took about 0.30 seconds in the browser worker;
the panel's 10 ms responsiveness timer had a maximum gap below 12 ms in that run.
These are host-specific smoke-test measurements, not performance guarantees.

A 12-probe experiment search found competing explanations across load planning,
allocation, and worker regions. For example, changing `sched.after_alloc.ext_tokens`
separates candidate explanations for nine downstream PCVs. That is an experiment
proposal from existing observations, not a validated vLLM intervention. The
synthetic program above supplies the independently measured validation.

A separate temporal holdout check discovered 102 equations using only the first
7,396 calls of this real trace. With preceding history retained, 99 held on the
later calls and three failed. For example,
`gc.lease_flush.queued = last(gc.launch.queued)` matched all 42 early target calls
but failed on 19 of 51 later target calls. This is a split of one execution,
not an independent run, and is evidence that even exact observed equalities can
be temporary. **Check on another execution** supports the stronger next step
when a new report is available.
