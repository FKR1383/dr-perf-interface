# Harder interfaces: real CPython hash tables

Collisions do not establish that an affine semantic interface is impossible.
These experiments instead expose three concrete difficulties: describing the
distribution of comparison lengths, accounting for quadratic table rebuilding,
and composing a container interface with user-defined equality work. They also
reproduce a checker limitation: averaging different inputs with identical PCVs
can conceal a missing cost variable.

This measures the installed, unmodified **CPython 3.12.3 `dict` implementation**,
with actual `PyDict_GetItemWithError` and `PyDict_SetItem` calls. The C helper
reads the real table layout but does not modify it or substitute an algorithm.
There are **154 physical cases**, checked both natively and under DynamoRIO:
80 integer lookups, 32 callback lookups, and 42 insertions. The checker is unchanged.

## Reproduce

Requires Linux, CPython 3.12 development headers, GCC, and the existing drperf build:

```sh
./build.sh
python3 examples/hash_table_cost/validate.py --study lookup --record
python3 examples/hash_table_cost/validate.py --study callback --record
python3 examples/hash_table_cost/validate.py --study insert --record
```

The scripts check dictionary results, instrumentation validity, marker call
counts, and the findings below. They save source/binary hashes, every case,
coefficients, unexplained cost, reconstruction errors, and independent case
audits in the three `*-evidence.json` files. Raw records remain under `out/`.
Assertions describe this implementation/build: compiler or Python changes can
require different PCVs. No large-input prediction or wall-clock claim is made.

## 1. Collisions plus variable-length integer comparisons: explained

Fixtures vary live size (8–512), insertion/deletion history, hits/misses, and
key length (4–256 base-2^30 digits). Adding multiples of `sys.hash_info.modulus`
constructs different positive integers with the same **complete hash**.
Equal keys are distinct objects, so successful comparisons cannot take the
pointer-identity shortcut. Deleted slots remain on some search paths.

A first semantic interface is:

```text
hash_digits, hash_subtractions,
probes_w1, probes_w2,
dummy_probes_w1, dummy_probes_w2,
hash_mismatches, equal_hash, eq_digits, hit
```

`equal_hash` counts equality calls. `eq_digits` counts all integer digits
examined by those comparisons. `_w1` and `_w2` gate counts on the table's
one-byte or two-byte index representation. All are computed from the entry
state, before the marker, by replaying the probe path.

| Annotation | Maximum unexplained share over observed states |
| --- | ---: |
| Size, capacity, deleted slots, key length, hit | 99.816% |
| Hash digits, probes, hit | 99.047% |
| The ten semantic PCVs above | 87.410% |
| Above plus comparison-length thresholds | **0%** |

The installed binary peels the first four digit comparisons out of its loop.
Consequently, total compared digits alone does not determine each basic block's
execution count. Add:

```text
eq_ge2 = number of comparisons examining at least 2 digits
eq_ge3 = number of comparisons examining at least 3 digits
eq_ge4 = number of comparisons examining at least 4 digits
eq_gt4 = number of comparisons examining more than 4 digits
```

These describe the distribution of comparison lengths, without naming machine
addresses. Which thresholds matter nevertheless depends on compilation.
The 14-PCV interface explains all measured lookup blocks; reconstruction error
is below `4e-11` relative, including the separate physical-case audit. Some
features are dependent on this restricted corpus, so individual coefficients
are not uniquely identified. This is observed-data agreement, not a universal
proof or a held-out test. See [lookup-evidence.json](lookup-evidence.json).

## 2. User-defined equality: a misleadingly successful checker result

The real dictionary holds keys with this equality callback:

```python
class WorkKey:
    def __init__(self, value, work):
        self.value, self.work = value, work

    def __hash__(self):
        return 42

    def __eq__(self, other):
        accumulator = 0
        for _ in range(self.work):
            accumulator ^= 1
        return self.value == other.value
```

The callback work changes neither the keys' hashes nor the equality results.
At eight live keys, successful lookups have identical container PCVs:
`used=8, probes=9, equal_hash=9, hit=1`. A probe sequence can revisit a slot,
which is why nine comparisons can occur with eight keys.

| Callback iterations per comparison | Instructions per lookup, including amortized wrapper cost |
| ---: | ---: |
| 0 | 16,226.44 |
| 8 | 37,949.44 |
| 64 | 190,164.13 |
| 256 | 712,039.63 |

No function of those four container PCVs can distinguish these inputs. Across
the full corpus, identical-PCV cases differ by up to **45.61x** in measured cost.

Yet the normal container annotation reports a maximum unexplained share of
only **0.0358%**. The collector merges invocations sharing PCVs; the fitter sees
their mean block counts. Because each size gets the same mix of callback work,
those means fit extremely well. The per-physical-case audit exposes up to
**1,429%** relative reconstruction error. This is a failure of using mean-fit
acceptance as evidence that the annotation explains individual inputs; it is
not a contradiction of a contract that explicitly promises only state means.

Adding the understandable PCV

```text
callback_iterations = sum(key.work for each equality call on the probe path)
```

reduces the independent audit's worst error to **1.082%**, with maximum
unexplained share **2.744%**. It is useful but not exact; Python interpreter and
allocation paths still contribute residual cost. See
[callback-evidence.json](callback-evidence.json).

For general object keys, a container-only interface cannot cover arbitrary
hash/equality callbacks. This example has a simple callback-specific interface.
Other callbacks need their own semantic PCVs, and callbacks that mutate the
table can additionally trigger lookup restarts. Those restarts are not measured
here. This does not prove that a compact interface is impossible for a given
callback.

## 3. Resizing: moved entries hide quadratic rebuilding

Fixtures cover capacities 32–2,048, dispersed and fully colliding hashes,
deleted prefixes, and insertions immediately before/at the resize threshold.
Each measured insertion gets a separately constructed dictionary. An insertion
is never repeated on an already-resized table. The harness validates the new
size, value, and predicted post-insertion capacity.

During a resize, CPython rebuilds the index by probing for each live entry.
In the largest collision fixture, **1,365 moved entries cause 933,387 occupied
slot encounters during rebuilding**. Replaying the table history supplies the
semantic PCV `rebuild_collisions`. Counting just moved entries leaves up to
97.854% unexplained cost.

The candidate interface adds resize-gated moved/deleted counts, index bytes,
rebuild and insertion collision counts, index widths, and counts of rebuild
chains with at least one/two collisions. The last thresholds account for two
peeled probe iterations in the installed binary. This reduces maximum
unexplained cost to **10.563%**, but **the interface is not accepted as a
successful explanation**: reconstruction errors remain large on small cases.

In particular, one state measures **303 instructions**, reports **zero
unexplained instructions**, yet its final formula predicts **870.92**. The
checker's per-block tolerance is `max(64, 5% of block cost)`, and its subsequent
slope pruning is not followed by an aggregate reconstruction check. Thus a
small unexplained share alone does not imply an accurate final cost formula.
The audit records this separately; it does not hide the error behind the
explained percentage. See [insert-evidence.json](insert-evidence.json).

Remaining unexplained blocks are principally in dictionary insertion and
`memcpy` paths. This experiment does not establish a minimal sufficient set of
PCVs for allocation/copy behavior or claim an impossibility result.

## Actual marker and audit boundary

[workload.py](workload.py) computes all PCVs before calling the C helper.
[native.c](native.c) marks these real operations (simplified here):

```c
perfmark_begin_v(region, n, names, values);
if (insert) {
    error = PyDict_SetItem(dict, key, seven);
} else {
    for (int i = 0; i < repeats; ++i) {
        PyObject *result = PyDict_GetItemWithError(dict, key);
        if (result) checksum += PyLong_AsLong(result);
        else if (PyErr_Occurred()) { error = -1; break; }
    }
}
perfmark_end(region);
```

There are 128 lookups per integer region, 16 per callback region, and one
insertion per insertion region. Each physical case/model is measured twice.
The separate `*_audit` marker uses `case_id` to retain input identity;
**case_id is never an explanatory PCV**. Audit costs are means of two calls,
not retained per-invocation block vectors. For insertion, audit and annotated
regions operate on equivalent separately allocated dictionaries, so allocator
state can differ. Callback specialization is warmed before measurement.

## Consequences for the framework

1. Branches can still have understandable PCVs, but counts of total work may
   need distribution summaries to satisfy a per-basic-block checker.
2. Container interfaces need to compose with callback interfaces. Probe counts
   alone do not explain work performed by arbitrary key methods.
3. To claim per-execution coverage, retain within-PCV variation or validate
   separate occurrences; a fit to merged state means cannot establish it.
4. Validate the final emitted formula's reconstruction error after tolerance
   and slope simplification. Report it alongside unexplained cost.

The last two are checker issues to address; the first two concern interface
expressibility and discovery. None of these results proves that no small
semantic affine interface exists.

Implementation references: pinned CPython 3.12.3
[dictionary source](https://github.com/python/cpython/blob/v3.12.3/Objects/dictobject.c),
[integer source](https://github.com/python/cpython/blob/v3.12.3/Objects/longobject.c),
and [table layout](https://github.com/python/cpython/blob/v3.12.3/Include/internal/pycore_dict.h).
Compiler peeling was checked against the installed binary's disassembly;
the evidence hashes that binary. Profiler symbols ending in `+?` are nearest
exported symbols and should not be mistaken for exact internal function names.
