# Composing interfaces across function calls

Run from the repository root (with drperf already built):

```sh
python3 examples/composition/run.py --thorough
```

This compiles and runs [app.c](app.c) under DynamoRIO, then checks 20 cases
against the actual trace. Each marked child is in another `noinline` function.
There are four runs: `-O2` baseline, new inputs, a deliberately changed child
count, and an independently compiled `-O0` baseline. Omit `--thorough` to skip
the last run. It retains one binary, `out/composition/report.txt`, the baseline
and held-out `.drperf.json` reports, and `validation.json` (about 8 MiB total).
Temporary raw files and the `-O0` binary are removed.

Ordinary `bin/drperf ./your-program` now prints composed interfaces too.
`DRPERF_REPORT=out/program.drperf.json bin/drperf ./your-program` additionally
stores the structured result under `composition`. Existing exclusive interfaces
and the explorer's per-region scenario behavior remain available.

## What the checker composes

First fit each region's own basic blocks and freeze those interfaces. A parent
uses `F_child` and `PCV*F_child` as its child terms, compactly written as
`(a*PCVs + d)*F_child`. The multiplier is fitted to the observed direct-child
call count, including zero-call parents. A child with unexplained work remains
an ordinary `F_child` reference; its unexplained component is retained.

Argument mappings are additional checked metadata, not requirements on the
parent formula. Varying or opaque arguments no longer produce a summation.
A single call is `F_child`; an affine number of calls is `(a*PCVs+d)*F_child`.
If call count itself cannot be expressed in that basis, the full child
contribution remains `unexplained(F_child)`. F denotes applications of the
child interface at actual child states, not a scalar global mean; numerical
inclusive predictions still need those states and any unexplained work.

## Measured examples

The baseline has 10,116 marked calls; the four runs have 49,660 calls in total.
On this build the child
`irregular_leaf(m)` was 99.8% unexplained: its hash-derived work count is
deliberately absent from its PCVs.

| Case | What appears in the parent interface |
| --- | --- |
| Repeated irregular child | `(2*n + 1)*F_irregular_leaf(m)` |
| Arguments change in a loop | `n*F_linear_leaf`; `m+j` is retained as argument metadata |
| Three levels across functions | `batches*F_middle(n,m)`, then `n*F_irregular_leaf(m)` |
| Data-dependent branch, incomplete parent PCVs | `unexplained(F_irregular_leaf)` until a call-count PCV is supplied |
| Same branch, add `selected_count` PCV | `selected_count*F_irregular_leaf(m)` |
| Identical parent PCVs, different hidden call counts | Marks the child multiplier unexplained; does not fit an average |
| Recursive function | A reference to `F_recursive(depth-1)`, with the observed base-case-dependent call count; no claimed closed bound |
| Multiple children | `n*F_linear_leaf(m) + (n+2)*F_irregular_leaf(m+1)` |
| Diamond call graph | `F_left(n,m) + F_right(n,m)`; each refers to the shared leaf without adding it again at the root |
| Rectangular nested loop, raw | Non-affine `n*width` multiplicity leaves the child contribution unexplained |
| Rectangular loop, refined | Declaring `cells=n*width` gives `cells*F_linear_leaf(m)` |
| Triangular loop, raw | Non-affine `n*(n-1)/2` multiplicity leaves the child contribution unexplained |
| Triangular loop, refined | Declaring `pairs=n*(n-1)/2` gives `pairs*F_linear_leaf(m)` |
| Conditional child argument, raw | `m<20 ? m : 2*m` cannot be replaced by an affine argument substitution; retains `n*F_linear_leaf` with unresolved argument metadata |
| Conditional child argument, refined | Declaring `effective=m<20 ? m : 2*m` gives `n*F_linear_leaf`, with `effective` in argument metadata |
| Alternating call sites to one child | Arguments `m,2*m,m,2*m,...` remain opaque; an affine invocation index does not explain the alternation |
| Mutual recursion | Both functions are marked recursive; `more=(depth>0)` explains the call count, but the target's own base-case flag remains a non-affine argument |
| Shared child with hidden caller context | Both callers retain `n*F_context_leaf_raw(m)`; numerical reconstruction deliberately fails despite an affine global state mean |
| Same child with context captured in its PCVs | Adding `units=m*(expensive?128:1)` gives the adjusted `F_child(m,units)=4*units+15`; the two callers pass `m` and `128*m` for `units` |
| Piecewise child cost | A two-regime child stays inside `n*F_regime_leaf(m)`; no parent refit or averaged regime |

The repeated-call case is particularly useful:

```text
F_irregular_leaf(m) = 36 + U_own_irregular_leaf(m)
F_repeated(n,m)     = 34*n + 33 + (2*n + 1)*F_irregular_leaf(m)
U_repeated(n,m)     = (2*n + 1)*U_irregular_leaf(m)
```

The unexplained child remains in the parent's **final** interface. The report
also retains the child's own unexplained breakdown by function and state.
The two factors in `(2*n + 1)` correspond to the proposed terms
`2*n*F + 1*F`; displaying them factored keeps the hierarchy readable.

The formulae above exclude identifiable marker blocks. On the measured run,
raw-count reconstruction using the separately saved raw fits and observed
unexplained tables matched every repeated-call parent's raw inclusive total
exactly. Across all four runs, `inclusive = self + direct children` held
exactly. The baseline three-level reconstruction had 0.016% aggregate absolute
error. Every case except the intended hidden-context negative control stayed
below 5% aggregate absolute reconstruction error per region. This checks the observed
execution, including its tabulated unexplained work; it is not an out-of-sample
prediction or a claim that the unexplained child became explained.

## Frozen relations on new inputs

The new-input run uses different `n` and `m` values, including values beyond
the baseline range. `composition.check` evaluates the **baseline** call-count
and argument relations against every new invocation; it does not fit new rules
and compare their coefficients. The result is 14,845 exact checks across 28
edges, with zero failures. Unknown child-call multipliers remain explicitly unexplained. Argument mappings
are checked separately and no longer block an affine multiplier.

The deliberately changed program performs `n+3` irregular-child calls where the
baseline performed `n+2`. The frozen checker rejects the multiplicity at all
40 parent invocations and records expected/actual values. Other relations still
hold. The `-O0` run passes another 10,363 frozen relation checks even though its
instruction costs differ. This separates structural relations from cost fits.

The instruction reconstructions for each run use that run's fitted own costs
and observed U tables. **Only the call-count/argument checks are held out.** We
do not claim held-out prediction of an irregular child's unknown cost.

## Negative control: a shared child hides caller context

The cheap caller runs `work(m)`, while the expensive caller runs `work(128*m)`
inside the same child marker, which initially declares only `m`. With equal
numbers of calls, the globally averaged child interface is:

```text
F_context_leaf_raw(m) = 258*m + 18   # recorded-count audit, before marker removal
```

It has zero unexplained work in the aggregated state means. Multiplying that
mean into the cheap caller gives **4,268%** aggregate absolute reconstruction
error; the expensive caller gives **49.43%** error. Both structural interfaces
still correctly say `n*F_child(m)`. This is why a child reference is not a promise
that its global state mean applies independently to every caller.

Declaring `units=m*(expensive?128:1)` in the child separates the contexts:

```text
F_context_leaf_refined(m,units) = 4*units + 18   # recorded-count audit
cheap child contribution       = n*F_context_leaf_refined(m,m)
expensive child contribution   = n*F_context_leaf_refined(m,128*m)
```

The refined child reconstruction is exact. Baseline parent errors fall to
2.014% and 0.023%, respectively (small own-block errors accepted by the existing
tolerance); both are exact on the new-input and `-O0` runs. The test requires the
raw cases to fail and the refined cases to pass. `report.txt` and
`validation.json` retain this result rather than silently excluding it.

For changing arguments, the checker learns `m+j` using the child invocation
index; it does not replace the calls with `n*F(mean_argument)`. If even that
argument relationship is not affine, it retains `n*F_linear_leaf` with unresolved argument metadata, with the observed
child states in the JSON evidence.

`branch_refined` computes `selected_count` before entering its region to
demonstrate the annotation. That extra computation is not an optimization or
a claim of a cheaply computable PCV. Its significance is that the same child
formula can compose once the parent names the relevant semantic quantity.

## Scope and checks

The composed section uses marker-adjusted instructions: identifiable perfmark
and native binding blocks are removed before fitting. No wrapper calibration is
subtracted. Python wrapper and caller-side argument preparation remain measured;
expensive PCV computation must be explicitly excluded using a `perf.pcv` region.
That region's own work is excluded from application interfaces and composition.
Raw instruction reconstruction tests explicitly use the saved `recordedRegimes`;
their reconstruction-error numbers describe the raw audit, not the marker-adjusted formulae.
Basic-block fits keep the existing instruction tolerances;
call counts and argument substitutions use exact rational checks, without the
instruction tolerance. Formulae are observations, not proofs over all inputs.

Only direct same-thread children are added, so three-level nesting does not
double count grandchildren. Cross-thread time overlap does not imply parentage.
Incomplete/malformed traces, dropped state buckets, and invalid measurement
metadata disable composition. Recursive cycles remain explicit recurrences.
There is no latency or parallelism inference.

```sh
python3 -m unittest discover -s tests -p test_composition.py
```

Tests also cover int64 argument values, rational coefficients, dependent PCVs,
single-state and two-state fits, zero calls, marker-removal preservation, and
legacy child interfaces with no exported fit. Additional checks use 100 seeded random affine
systems and contradictory samples, 20 random nesting forests checked against
an independent interval-containment oracle, and a 1,200-level call chain.
They cover missing/new children, changed schemas, malformed numeric states,
argument order after sorting JSON keys, and all members of recursive cycles.
