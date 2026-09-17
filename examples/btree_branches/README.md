# B-tree branches: a real test of the framework

## Current behavior: both implementation issues are fixed

The checker now accepts valid negative intercepts, and the C client, Python
bindings, and Rust binding retain all declared PCVs using dynamically sized
storage. There is no fixed four-PCV limit. Existing state-count and memory
budgets still apply.

The current regression uses six PCVs directly through `perfmark_begin_v`,
including the original `depth` expression. Both the depth and descents
interfaces have **zero unexplained blocks**, with relative reconstruction
error below 1e-9. This was checked on **120 tree/query cases, depths 2–8, up to
524,288 keys**, and 184,320 lookups both natively and under DynamoRIO. Every
physical tree/query case is also checked separately, so feature-state averaging
cannot hide a failed prediction.

```sh
./build.sh
python3 -m venv out/btrees-study/venv
out/btrees-study/venv/bin/pip install -r examples/btree_branches/requirements.txt
out/btrees-study/venv/bin/python examples/btree_branches/fixed.py --record
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

See [fixed.py](fixed.py) and [fixed-evidence.json](fixed-evidence.json). The
unit/integration tests additionally cover PCV translation, genuinely curved
counts, and 0–64 PCVs through C, Rust, Python's C extension, and ctypes.

The remainder of this document and the original `evidence.json` /
`deeper-evidence.json` describe the **pre-fix investigation at commit
`ffa8bbe`**. Its `validate.py` and `deeper.py` deliberately assert the old
failure and should be run on that revision; use `fixed.py` on current code.
The blockwise acceptance criterion itself remains unchanged.

## Historical investigation

**Dynamic branching does not prevent a small semantic affine interface in this
experiment. The current checker nevertheless rejects useful interfaces.** Two
causes are its stronger per-basic-block requirement and its negative-intercept
heuristic. Its four-PCV marker limit also prevents declaring the six natural
event counts that explain these lookups exactly.

This studies the unmodified **Python BTrees 6.1 C extension**, specifically
`IIBTree` with integer keys and values. CPython's built-in `dict` is a hash
table, not a B-tree ([Python FAQ](https://docs.python.org/3/faq/design.html#how-are-dictionaries-implemented-in-cpython)).
The older Ditto case in this repo uses Rust `BTreeMap` behind a Python API;
these are different implementations and these measurements do not validate
that older case.

## Reproduce the historical investigation (revision ffa8bbe)

From the repo root, with drperf already built:

```sh
python3 -m venv out/btrees-study/venv
out/btrees-study/venv/bin/pip install -r examples/btree_branches/requirements.txt
out/btrees-study/venv/bin/python examples/btree_branches/validate.py --record
```

[workload.py](workload.py) constructs actual trees and computes semantic PCVs
before entering the region. [measure.c](measure.c) calls the installed BTrees
extension through `PyObject_GetItem`; it does not replace the lookup algorithm.
The native wrapper removes Python-loop noise. Each region performs 256
identical lookups, twice, with the same marker boundary for all annotations.

There are 72 tree/query cases: sizes 128,512,2048; ascending, descending, and
fixed-seed shuffled insertion; eight query ranks per tree. The documented
node-size settings are set to eight to exercise multiple levels on small
inputs. All queries hit, all values equal seven, and trees are resident and
read-only. This does not cover misses, insertion/splits during measurement,
deletion, string/object comparisons, or persistence I/O.

184,320 lookups were correctness-checked both natively and under DynamoRIO.
Instrumentation validity and call counts passed. Raw records stay in `out/`;
[evidence.json](evidence.json) includes every input/path summary, measured
point, fitted model, frozen prediction, dependency version, and binary/source
hash. The checker itself is unchanged.

## What the dynamic branches actually do

This implementation performs binary search among an internal node's separator
keys, descends to one child, and finally performs binary search inside a leaf
bucket. Internal separator equality ends that node's search but still descends;
leaf equality ends the lookup. See the pinned upstream
[internal search macro](https://github.com/zopefoundation/BTrees/blob/6b505c85044014c94b379bce25fa6046fbabb405/src/BTrees/BTreeModuleTemplate.c#L316),
[tree traversal](https://github.com/zopefoundation/BTrees/blob/6b505c85044014c94b379bce25fa6046fbabb405/src/BTrees/BTreeTemplate.c#L234), and
[leaf search](https://github.com/zopefoundation/BTrees/blob/6b505c85044014c94b379bce25fa6046fbabb405/src/BTrees/BucketTemplate.c#L38).

The number of comparisons depends on each visited node's occupancy and the
query's position among its keys. Insertion history changes the shape even when
the logical mapping is identical. For example, two measured queries have the
**same size, depth, key, and rank**:

| Tree construction | Size | Internal nodes visited | Query key / rank | Comparisons | Instructions per lookup |
| --- | ---: | ---: | --- | ---: | ---: |
| Ascending insertion | 512 | 3 | 1002 / 1 | 10 | 473.05 |
| Descending insertion | 512 | 3 | 1002 / 1 | 7 | 440.05 |

Thus no exact function of just size, depth, and rank can distinguish these
two costs. This is an information loss in those summaries, not a proof that
all understandable PCVs fail.

Even depth plus total comparisons is not exact: cases 69 and 56 both visit
three internal nodes and make 12 comparisons, but cost 480.05 and 495.05
instructions respectively. Their distributions of less-than, greater-than,
and equality outcomes differ. In all tables, instructions include the C API
wrapper and amortized marker overhead, not solely the B-tree search body.

## Failure 1: requiring every block to fit is stronger than explaining cost

A region-level fit using only two meaningful PCVs works well:

```text
D = internal nodes visited
C = total key comparisons

instructions per lookup = 265.1106 + 36.0561*D + 9.2636*C
```

This formula was fitted on the 48 cases of sizes 128 and 512, then frozen.
Its worst error is **1.83% on training cases and 2.18% on the 24 held-out
2048-key cases**. These are designed study cases, not a blind discovery trial
or a guarantee for larger trees or other workloads.

Yet drperf with `D,C` reports **up to 44.50% unexplained cost**. The negative
intercept rule contributes, but is not the whole issue: evaluating only the
per-block fit tolerance, allowing any intercept, still rejects blocks
accounting for up to **33.57%** of an individual case's instructions.

The reason is that total comparisons do not determine how that work is divided
among the branch-specific blocks. Costs of those blocks vary together, and
their aggregate admits a much better fit than the blocks individually do.

This is consistent with drperf's current blockwise contract. It is a framework
limitation if the intended acceptance question is instead, "Does a small
semantic affine interface explain the region's total cost within tolerance?"

A possible change is to report a directly checked region formula alongside
the stricter blockwise explanation. Keep attribution and within-state
variation visible; do not silently reinterpret a good fit of averages as
a guarantee about each execution. This experiment preserves each tree/query
case with a separate audit key for all direct-fit and holdout checks.

## Failure 2: the checker rejects exact affine block formulas

Six natural summaries explain every measured block exactly before applying
the negative-intercept heuristic:

| PCV | Meaning |
| --- | --- |
| D | Internal nodes visited |
| IL | Internal separator comparisons where stored key < query |
| IG | Internal separator comparisons where stored key > query |
| IE | Internal separator comparisons where stored key = query |
| LL | Leaf comparisons where stored key < query |
| LG | Leaf comparisons where stored key > query |

There is exactly one leaf equality for every successful lookup in this
workload, so that cost belongs to the constant. The discovered total is:

```text
instructions per lookup = 272.05078125
                       + 34*D + 10*IL + 11*IG + 3*IE + 9*LL + 11*LG
```

Coefficients fitted on the smaller trees predict every held-out larger-tree
case exactly to floating-point precision. Cases sharing all six PCVs have
identical measured totals; this result is not created by averaging away
different totals.

Nevertheless the checker reports up to **12.18% unexplained**. Six blocks
inside `_BTree_get` have valid formulas of the form:

```text
block cost per lookup = k*(D - 1) = k*D - k
```

They execute on descents between internal nodes. The fitted negative constant
causes `derive_regime` to reject them, although their counts are nonnegative on
the input domain and their fits have essentially zero residual. The recorded
values of `k` are 6,2,4,3,2,4; evidence includes their module offsets.

Changing the PCV from `D` to `descents = D-1` gives **zero unexplained cost**
with the same six-feature affine space. An affine checker should not change
its verdict under this translation. The heuristic was intended to reject
misleading curve fits, but here it rejects an exact loop-count identity.

The repair is to account for the PCV domain and predicted counts, rather than
treating a negative intercept alone as invalid. Merely shifting the annotation
demonstrates the issue; it should not be a burden placed on the annotator.

## Marker capacity versus mathematical expressibility

The current marker accepts at most four PCVs. Therefore the six-feature
experiments above are **offline applications of the existing affine checker
to the same measured block vectors**, using PCVs computed before measurement.
They are not presented as a supported six-PCV marker run. The four-feature
annotations that were tried still leave substantial unexplained cost:

| Annotation | Maximum unexplained share |
| --- | ---: |
| Size, depth, rank | 45.00% |
| Depth, comparisons | 44.50% |
| Depth, internal comparisons, leaf comparisons | 33.39% |
| Previous three plus total less-than outcomes | 33.39% |
| Six semantic events, offline | 12.18% |
| Same six, replacing depth with descents, offline | 0.00% |

This does not prove that every possible choice of four understandable PCVs
fails. It demonstrates an exact, understandable six-PCV solution and a useful
approximate two-PCV solution. Neither requires encoding a whole branch path as
an opaque integer or declaring the instruction count itself.

The dynamic branch paths are irregular, but the meaningful event vocabulary
remains small here. For the proposed calculus, distinguish:

1. Whether a semantic PCV family can represent the total cost.
2. Whether it can represent every block's count separately.
3. Whether the checker accepts equivalent affine representations consistently.

These measurements separate all three questions. They support a concrete
critique of the current framework without asserting that B-trees are
fundamentally inexpressible.

## Follow-up: what is semantic here, and does it survive deeper trees?

The proposed interface is a fixed collection of functions of the actual tree
and query key:

```text
PCVs(T, q) = (internal_descents(T,q),
             internal_less(T,q), internal_greater(T,q), internal_equal(T,q),
             leaf_less(T,q), leaf_greater(T,q))
```

They count meaningful search operations along the path selected by the query.
They do not store native instruction counts, coefficients, or an encoded path
identity. `path_summary` evaluates them from the tree's state before the
measured lookup. It does replay the search decisions: this is an
implementation-aware interface, not an abstraction using only mapping size
and height. Calling it "good" means it is compact, interpretable, and has a
fixed number of features as the tree grows; it does not establish that this is
the abstraction an application author wants.

Using descents `E=D-1`, the measured interface becomes:

```text
instructions per lookup = 306.05078125
                       + 34*E + 10*IL + 11*IG + 3*IE + 9*LL + 11*LG
```

To address the shallow original range (depths 2–4), run:

```sh
out/btrees-study/venv/bin/python examples/btree_branches/deeper.py --record
```

This builds 8,192-, 32,768-, 131,072-, and 524,288-key trees in each insertion
order, tests eight query ranks per tree, and measures 98,304 lookups natively
and under drperf. All construction finishes before the first marker. The
96 new cases cover internal-node depths **4–8**, versus 2–4 originally, with
the largest tree **256 times** the old maximum size. Node capacity settings
remain eight; these are still deliberately small-fanout trees, not a test of
the default capacity settings.

Both predictive formulas are frozen from the original 128/512-key training
cases, and the target binary/checker hashes are verified against that baseline.
The follow-up does not retrain them on the larger trees:

| Check on new cases | Result |
| --- | ---: |
| Frozen depth/comparisons formula: worst total prediction error | 3.008% |
| Frozen six-count formula: worst total prediction error | Below 1e-9 relative |
| Fresh drperf blockwise fit with depth/comparisons: maximum unexplained | 60.52% |
| Fresh six-count blockwise fit with depth: maximum unexplained | 19.94% |
| Fresh six-count blockwise fit with descents: maximum unexplained | 0.00% |

The six-count checker calls remain offline because the marker limit is four.
See [deeper-evidence.json](deeper-evidence.json) for every frozen prediction,
path, raw-data hash, and the baseline evidence hash. Eighty of the 96 new cases
have depth greater than four.

This extends the empirical evidence; it is not an all-depth proof. Such a proof
would establish the per-event cost identities compositionally under explicit
assumptions about key types, hit/miss behavior, and resident node state.
