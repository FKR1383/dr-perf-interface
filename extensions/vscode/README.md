# drperf Region Explorer

Inspect what each region's cost depends on, then explore how a change to one or
more performance-critical variables (PCVs) could affect other regions. The
explorer does **not** add region costs into a total or predict latency,
parallelism, GPU overlap, or scheduling.

## Region execution graph

Open a performance report and select **Graph**. The upper canvas shows region
names, nesting, and relationships. The bottom panel shows the selected region's
composed formula, unexplained share, function breakdown, and observed states.
Click a region name to update the bottom panel without opening source or resetting
the graph's scroll position. The panes scroll independently.

**Expand all** reveals every region across the full profile; **Collapse all**
returns to the outermost boxes. Both buttons stay at the front of the toolbar.
A triangle expands just that region. The layout keeps a fixed left-to-right
order: expansion makes space for children and moves later boxes to the right.
The viewer preserves zoom, scroll, and keyboard focus, without shifting the
entire viewport to follow the clicked node. The existing graph stays visible
while ELK computes the updated layout. Formulas
stay in the bottom panel, retaining symbolic `F[child]` terms. Clicking a child term
reveals and selects that child without leaving the graph. Expansion does not
refit coefficients or add child costs a second time.

[ELK.js](https://github.com/kieler/elkjs) lays out nested regions and routes the
edges using a horizontal layered layout with sibling-order constraints. These
constraints only control placement; they are never displayed or reported as
dependencies. Layout positions carry no timing meaning. **Show sequence** adds gray arrows for
observed sibling order; these are hidden by default to emphasize waits. **Blue dashed arrows show
recorded waits**, pointing from the waiting region to the region that published
completion. Arrows have no duplicate endpoint labels or edge numbers. Exact
endpoints and observations appear in the selected region’s bottom panel.
Click a wait arrow or **Reveal endpoints** in that panel to reveal both regions. Nesting paths come from the actual
captured invocations, so the same region called under different parents is not
arbitrarily assigned to one parent. Wait arrows only connect distinct regions.
Same-region synchronization stays in the raw report but is excluded from the graph.
When two distinct endpoints are inside one collapsed box, select that box and
use **Reveal endpoints** in its bottom panel; no self-loop is drawn.

Use **Full graph** for outermost regions or **All waits** to see the containers
with matched waits across the profile. **Full-screen graph** maximizes the
viewer; Escape restores it. **Fit graph** shows an overview; use **100%** and scroll horizontally to read individual names.
Graph expansion stays in the viewer. Use **Open source** explicitly or
the **Interface** tab for a region's complete interface. Threads are never graph nodes.

**Export graph as HTML** saves a single interactive file containing the complete
profile and viewer. Open it in a modern browser for a full-window graph with
expansion, clickable child formulas, wait links, and zoom. No server, internet,
VS Code, or profiler is required. Export preserves the current graph view;
**Full graph** lets you explore the rest of the embedded profile. With Remote
SSH, use VS Code's Files view to download the saved HTML if you saved it remotely.

Existing complete profiles work directly, without rerunning the program or
opening a separate HTML file. New exports include checked affine edge-count
formulas. Older exports derive sequence/nesting and captured producer links
from their trace, without inventing count formulas. Profiles without wait data
say so; incomplete wait captures do not produce producer edges.

The graph does not infer latency, contention, or required dependencies from
observed sequence. Counts refer to all captured invocations, not just a request.

## Install and open

Install the packaged `.vsix` with VS Code's **Extensions: Install from VSIX**
command, or:

```sh
code --install-extension drperf-explorer-0.1.7.vsix
```

Start with **drperf: Open Joint-Change Demo** for a ready-to-inspect scenario:
two changed PCVs, checked relationships, per-region effects, and comparison with
an independent measured execution. Its assumptions are visible and editable.

Run **drperf: Open Producer/Consumer Demo** from the Command Palette for a
self-contained example measured by drperf. No profiler or GPU is needed to view
it. The bundled example has concurrent producer/consumer threads, ordinary
affine regions, a branch with two fitted regimes, and a lookup whose cost is
partly unexplained.

To inspect your program, build drperf and save a report during the normal run:

```sh
DRPERF_REPORT=out/my-program.drperf.json \
DRPERF_SOURCE_ROOT=. bin/drperf python app.py
```

Or export measurements you already have:

```sh
bin/drperf-export out/raw --source-root /path/to/project \
  -o out/my-program.drperf.json
```

Then run **drperf: Open Performance Report**. Open the `.drperf.json`, not its
adjacent `*.waits.<hash>.jsonl.gz`
evidence file. The JSON retains formulas, breakdowns, region traces, graph
endpoints, and checked wait results; full native synchronization histories are
loaded only by the command-line checking tools. Keep the evidence file beside
the JSON if you need to recheck the capture.

The **drperf Regions** tree appears
in the Explorer. Clicking a region in the tree or interface list opens its
source beside the performance panel at the annotation. Graph expansion stays
in the graph; use its explicit source action to open code. For
regions with multiple source locations, the first opens automatically; use the
file-and-line links to choose another. If the files live outside the current
workspace, set `drperf.sourceRoot` to the source directory used at export.

Clicking a region's CodeLens, choosing **Inspect Region at
Cursor**, or moving the cursor into a region while the panel is open selects its
interface. Hovering over the annotation shows a compact formula. Source hashes
flag code that has changed since export.

For fresh Qwen/Kimi captures under GX, use the
[Ditto-KV capture and export guide](../../examples/explorer/DITTO_KV.md). It
covers staging the current profiler, recording both workloads, checking the
raw measurements, and exporting source-linked JSON profiles. Formula comments
are not inputs to the viewer.

Costs and percentages display as whole numbers; fitting and scenario arithmetic
retain their original precision. A displayed zero coefficient may be a small
nonzero value. Exact call counts and argument substitutions retain fractions.

The unexplained badge follows the displayed composed interface: its numerator is
own unexplained work plus the **full subtree cost** of each
`unexplained(F[child])` term. Its denominator includes own work and all direct
child subtrees. A child with a fitted multiplier is an atomic explained term at
its parent, even when that child has unexplained work internally. Click the child
to inspect that work. The parent badge and region sidebar use this same scope;
charts and function attribution are explicitly limited to own work.

Child costs are estimated by replaying the complete recorded nesting with the
measured exclusive mean for each child PCV state. Parent calls are averaged
within each state, then distinct states have equal weight, matching the own-fit
summary. These are instruction shares, not latency or exact per-call inclusive
counts. They are labeled as estimates. Missing or invalid child evidence shows
an unavailable share, never an own-only zero. Positive shares that round to zero
display as `<1%`. The “Tied PCVs” badge is hidden; declared PCVs and dependency
metadata remain intact for checking and scenario support.

This display change works with existing complete JSON exports; no new capture
or re-export is required.

## Four views

- **Interface:** affine formulas, PCV ranges, observed states, unexplained work,
  per-function attribution, source links, and suggestions for the next small
  experiment. Parent formulas retain direct children as clickable `F[child]`
  terms. Click one to inspect the child without expanding its formula in the
  parent. Each child retains its unexplained work and descendants; irregular
  call multipliers remain unexplained. Argument mappings are separate metadata
  and never force summation notation. Charts and attribution show own work.
- **Relationships:** the full list of discovered state equalities and a compact
  dependency diagram. `last`, `cum`, `cumend`, and `count` retain their distinct
  meanings. Search is by region, PCV, or operation. The diagram is a dependency
  view of equations, not a causal or timing graph. Check these equations on
  another execution even if its call structure differs.
- **What-if:** edit one or more PCVs using multiply/add/set, explicitly choose
  observed equations as assumptions, and inspect the affected regions. Results
  show mean explained instructions per call over the same recorded calls,
  changed PCVs, unknown cases, and extrapolation. Save the scenario and results
  as JSON for review or agent use. **Open Saved Scenario** checks and restores
  it against its original report.
- **Compare runs:** compare observed costs at exactly shared PCV states across
  two reports, with equal weight per shared state within each region. It can
  reveal coefficient changes without confusing
  a different workload mix with a change in the region's cost.

## What a scenario means

A scenario replays the recorded marker sequence. At each region entry, selected
relations compute new state values from preceding calls; direct interventions
are then applied. `cumend` includes only calls that ended before that entry.
Histories reset at each process/run boundary. Call counts, nesting, and marker
order stay fixed. The replay makes no assumption about elapsed time or
concurrency beyond that recorded sequence.

`last` means the latest preceding **entry**, `cum` sums preceding entries, and
`cumend` sums only calls whose end markers precede the current entry. Two
overlapping producers can therefore have different begin and completion
histories. Cycles in the relationship graph are allowed because references
always read prior history, not simultaneous equations at the current entry.
When replay's trace and arithmetic checks pass, and selected equations hold on
the original trace, an identity intervention reproduces its original PCV
states. This follows by induction over the recorded
markers; it establishes replay consistency, not realizability of a new input.

A relationship that held in the measurements is **observed evidence**, not proof
of causality. Choosing it for a scenario is an explicit assumption. Alternative
equations can coincide in the original trace and disagree after an intervention;
choose one per target PCV. Direct interventions override the selected relation
for that target.

The checker only accepted formulas at observed states within its tolerance.
Unobserved points and extrapolations are labelled. A gap between fitted regimes
has no assumed branch boundary; overlapping ranges do not select a branch by
array order. An extrapolated point lies outside the regime's per-PCV min/max
ranges; an unobserved point is a new combination inside those ranges. These
labels do not establish input feasibility or generalization. New combinations of correlated PCVs are not
identifiable. Unexplained cost at changed states remains unknown, and partial
predictions show how many calls were modelled. Large int64 PCVs are preserved as
strings in reports rather than rounded; the current JavaScript replay rejects
states outside its exact integer range.

Relationship discovery is bounded and not exhaustive. Reports say when a search
or trace limit prevented exploration. A missing or incomplete trace, counter
validity errors, or invalid trace sequences prevent scenario replay. Viewing
recorded interfaces is still possible.

## Configuration

- `drperf.sourceRoot`: root for the relative source paths in a report. Defaults
  to the captured source root when it is inside an open workspace, otherwise
  its workspace folder. Python context managers/decorators and literal C/C++
  and Rust marker calls are supported. Dynamic names need manual navigation.
- `drperf.codeLens`, `drperf.followCursor`: toggle source decorations and cursor
  tracking.
- `drperf.pythonPath`, `drperf.exporterPath`: executables used only by the explicit
  **Export Raw Measurements** command. Exporting executes Python and requires a
  trusted workspace. Opening a report does not execute its measured program.

Reports contain local names, source paths, PCV values, and measurement metadata.
The extension performs no telemetry and sends no report data to a service. It
works with local or remote VS Code extension hosts; the viewer itself does not
need DynamoRIO or Python.

Scenario checks, comparisons, proposals, and experiment searches run in a local
web worker so the panel remains responsive. Only extension assets are loaded;
reports stay local. New edits supersede queued scenario work, and stale results
cannot replace a newer edit or report.

## Build and test

Developer tooling requires Node.js 22 or later. The extension has no runtime npm
dependencies.

```sh
cd extensions/vscode
npm ci
npm test
npx playwright install chromium
npm run test:ui
# Linux extension-host test (requires Xvfb):
xvfb-run -a node test/run-host.cjs
npm run package
```

The tests include actual VS Code activation, CodeLens, hover, cursor mapping,
and stale-source detection; browser checks cover the interactive panel. The
backend tests live in `tests/test_explorer.py`. Regenerate the measured example
with `examples/explorer/run.sh` from the repository root.

Implementation uses VS Code's [Webview API](https://code.visualstudio.com/api/extension-guides/webview)
and [programmatic language features](https://code.visualstudio.com/api/language-extensions/programmatic-language-features).

## Propose, check, and validate relationships

The What-if panel accepts proposed **state relationships**, including products,
integer powers, and conditional expressions. For example, target `lookup.pairs`
with `last("dequeue", "items") ** 2`. The checker reports counterexamples or
confirms agreement at every recorded target call. A separate button adopts a
checked proposal as a scenario assumption. Cost interfaces remain affine;
PCVs themselves are still expressions in the measured program's language.
The small expression editor is only a notation for cross-region relationships.

History references are `last("region", "pcv")`, `cum(...)`, `cumend(...)`, and
`count("region")`; absent prior history is zero. Arithmetic uses exact integers
with `+`, `-`, `*`, `//` (floor division), `%`, and `**` (exponents 0..16).
Comparisons and `condition ? then : else` express piecewise relationships.
Expressions are parsed, never evaluated as JavaScript. Their size and arithmetic
are bounded. Unsupported expressions require a different annotation or an
external checker; the editor is not a general program interpreter.

**Compare against a new measured report** checks a changed execution. It first
requires matching call counts, marker order, thread roles, and nesting. Groups
are paired by their order in the reports, with threads matched by first
appearance; unrelated process sets should not be compared this way. State
matches and cost errors are reported separately. Cost checks use observed
per-state means and omit predictions with unexplained blocks or unsupported
states. Different instrumentation settings are rejected. This is evidence for
a specific intervention, not a universal proof.

The [measured example](../../examples/explorer/README.md) demonstrates both a
failed extrapolation and a successful PCV refinement. **Open Refined PCV Demo**
opens its improved interface. For agents and terminal workflows:

```sh
bin/drperf-explore report.drperf.json --list
bin/drperf-explore report.drperf.json --edit producer items scale 2 \
  --relation RELATION_ID --validate changed.drperf.json -o scenario.json
```

Scenario JSON includes each changed region, coverage and support labels,
representative calls, and the actual history values used by their equations.
It contains no cross-region total or latency estimate.

The CLI exits nonzero for malformed or unsupported inputs. A completed analysis
can still contain failed equations or validation mismatches; agents should
inspect the structured result fields rather than treating exit code zero as a
claim that every prediction held.

## Recorded counts and marker exclusion

The default view uses drperf's marker-adjusted formulas. **View recorded
counts** restores the separately fitted raw block counts, retaining the marker API's
instructions in each region's own cost. The selected basis also applies to
scenario validation and is saved with the scenario. The terminal equivalent is
`--recorded`. CUDA/native exclusions and OpenMP-wait exclusions are unchanged.

Marker-module blocks are excluded by identity. No wrapper calibration is
subtracted. Python wrapper and caller-side preparation remain measured unless
explicitly excluded; work inside `perf.pcv` regions is omitted from application
interfaces. This avoids estimating away application work in shared interpreter
blocks. Small boundary overhead can still matter for very small regions.
Re-export older raw captures to apply this accounting; loading an existing JSON
does not recompute its formulas or remove its old calibration diagnostics.
Older saved reports can still contain the legacy over-subtraction and negative
calibrated costs. Their recorded-count view retains the old inverse adjustment;
new reports use `recordedRegimes` because a constant-only inverse is insufficient.

If one region name is used with different sets of PCV names, the exporter creates
separate interface variants with stable IDs. Reordering the same named PCVs does
not create a variant. Each variant keeps the original source links; its schema
appears in the display name. This prevents values for one PCV from being fitted
under another PCV's name.

## Find an experiment that distinguishes explanations

Enable **Compare alternative relationships** in a scenario. The checker first
verifies each candidate on the original trace, then compares its prediction to
the selected equation using the scenario's history at each target call. A
disagreement identifies a possible discriminating experiment. It is a one-step
comparison in that history, not a full alternative replay or a measured failure.

For example, the demo supports both `copy.bytes = 8*last(decode.tokens)` and
`copy.bytes = 16*last(dequeue.items)`. Changing decode's expansion factor makes
them disagree. If that change is implemented in the program, a small measured
run can tell which equation survives. This helps distinguish accidental
correlations from relationships useful under an intended change. The CLI flag
is `--audit-alternatives`.

**Find distinguishing experiments** searches from the recorded baseline using
your selected relationship assumptions. It tries `add 1` and `multiply by 2`
on source PCVs of competing equations, prioritizes sources that participate in
more ambiguous targets, and checks up to 12 probes. Suggestions rank by how many
target PCVs they separate, not by aggregate cost. The panel records rejected
probes, including changes that produce non-integer states under an assumption.

These are candidate PCV interventions, not generated program inputs. You still
need to implement a realizable input/configuration change, check that the fixed
call structure is appropriate, and measure it. A missing suggestion is not
proof that the equations are equivalent. The CLI can raise the search budget
to 64 probes:

```sh
bin/drperf-explore report.drperf.json --assume-first \
  --suggest-experiments --max-probes 12 -o experiments.json
```

Every suggested scenario retains its selected equations and checked proposals,
so it can be replayed independently. The measured demo's decode expansion
experiment is found automatically by this search.

## Compare interfaces across runs or versions

**Compare runs** pairs interfaces by original region name and PCV names. It
compares measured per-state means only at exactly shared states, regardless of
call order. States without a counterpart remain unpaired; negative calibrated
costs are excluded. The panel also shows both formulas and identifiable
coefficient differences, and flags changes to captured PCV source expressions.
PCV meanings still need to be consistent across the reports.

```sh
bin/drperf-explore before.drperf.json --compare after.drperf.json -o comparison.json
```

Unlike scenario validation, this comparison does not need a complete trace or
unchanged call counts. It needs valid instruction measurements with matching
measurement settings. Each region remains separate, and the observed
differences are not a statistical significance test. The portable report
[schema](schemas/report.schema.json) also enables validation and completion
when editing `*.drperf.json` in VS Code.

## Recheck relationships on another execution

In **Relationships**, choose **Check on another execution**. Each reference
equation is first checked on its original trace, then on the new report's actual
history. This check allows different call counts, nesting, thread interleaving,
and process/run groups. It predicts no costs. Histories reset for each new
process/run, and schemas are matched by original region name and PCV names.

Results distinguish equations that still hold, equations with counterexamples,
unavailable schemas, and targets the new run did not exercise. Changed captured
PCV expressions are flagged, since matching names alone cannot establish matching
semantics. Checked proposals from the What-if panel are included.

```sh
bin/drperf-explore before.drperf.json --check-relations after.drperf.json \
  -o relationship-check.json
```

This is separate from fixed-trace scenario validation: it tests a state equation
against what actually happened, instead of predicting a changed execution from
the old marker sequence.


Declared event annotations (`event_publish` / `event_waited`) appear in **Graph →
All waits**. Blue dashed edges are ordered in the observed run; red dashed edges
are violated declarations, and amber indicates unverified declarations with known
endpoints. Each arrow names the actual consumer and publisher; clicking it reveals
both nested regions. Baseline/probe status and violation counts appear above the
graph. Ordered and violated observations of the same region pair remain separate.
Existing JSON reports containing `eventModel` can be opened without reprofiling.
The exporter also includes these relationships in `executionGraph`.

A small real Ditto CPU example is available at
`out/waits/ditto-events/correct-probe.drperf.json`; compare it with
`out/waits/ditto-events/premature-probe.drperf.json` to see deliberate violations.


Graph layout measures wrapped region names before passing dimensions to ELK.
ELK arranges nested groups and routes edges; no custom placement algorithm is
used. The graph fits automatically when opened and takes about 90% of the view
by default. **Details** toggles the selected region's performance panel below
it. **More** holds view filters, collapse, sequence, export, legend, and **100%**;
it also lets you show or hide the region list. Zoom and canvas scroll survive
selection. **Fit** shows the whole layout again. Click a wait arrow to reveal
its publisher. Full screen and offline HTML use the same library and layout.


The graph opens in **Full graph**. **Expand all** reveals every captured nesting
path; node actions remain inside the graph. The two-region candidate-future
experiment is a focused test, not the full Ditto serving profile. On this machine
the full profile is `/home/ubuntu/compression/ditto_kv/example/qwen2.5B/qwen.drperf.json`
(105 regions, 133 nesting boxes, one cross-region wait relationship; same-region
synchronization is retained only in the raw report).
Edge numbers count repeated observed checkpoints/API calls, not distinct
dependencies or times the CPU blocked. Where fitted, the count per consumer
invocation is shown separately. The candidate test has one dependency observed
across ten `get` calls, not ten different dependencies.

The extension bundles ELK.js 0.12.0 locally in `media/vendor/`; the offline HTML
includes the same library. Its Eclipse Public License is included as
`media/vendor/ELK-LICENSE.md`. The adapter in `media/graph-layout.js` maps region
nesting and observed edges to ELK, then translates its output to SVG coordinates.
