# Synthetic limits of drperf

Six runnable C kernels show both rejected interfaces and misleadingly good
fits. Each has a repaired annotation. The checker discovers every coefficient;
the annotations supply only PCV expressions in the program's own language.

Run from the repository root, after `./build.sh`:

```sh
python3 examples/drperf_limits/validate.py
# Refresh the checked-in evidence after all assertions pass:
python3 examples/drperf_limits/validate.py --record
```

The script compiles [programs.c](programs.c), checks 519 calls natively against
independent result oracles, then repeats them under actual DynamoRIO/drperf.
It checks instrumentation validity, fitted interfaces, counterexamples, and
repairs. No benchmark collection files or checker implementation are changed.
Raw measurements go under `out/drperf-limits-*`; compact per-state measurements,
formulas, frozen predictions, build command, and source/binary hashes are in
[evidence.json](evidence.json). This is an executable development suite, not an
agent evaluation or a timing benchmark.

## Results

Recorded with GCC 13.3.0, `-O2`, vectorization and loop unrolling disabled.
Instruction coefficients depend on the build. All six repaired interfaces have
zero unexplained instructions and numerical reconstruction error below 1e-9
relative on these observed states.

| Case | What goes wrong | Observed result before repair | Repair |
| --- | --- | --- | --- |
| Nested loops | Missing interaction | Up to 100% unexplained | Add `n*m` |
| Branch inside a loop | Work saturates at a boundary | Up to 96.31% unexplained | `min(x,y)` and `max(x-y,0)` |
| Data-dependent branches | Equal PCVs collapse different executions into a mean | 0% unexplained despite almost 10x cost variation | Expose branch counts; check variation within a state |
| Correlated training inputs | Wrong variable predicts the training set | `106*n+20` passes when `m=n` | Vary inputs independently and freeze the model for validation |
| Unseen branch | Small tests miss a quadratic path | Small-input fit underpredicts larger cases by over 98% | Exercise the boundary; add conditional PCVs |
| Tiny irregular branch | Absolute block tolerance masks numerical error | 0% unexplained, but up to 77.65% formula error | Add branch indicator; separately check reconstruction error |

Here “passes” means at most 5% unexplained instructions at every observed state,
with enough states and valid instrumentation. Automatic regime splitting is
disabled. The existing block fit uses `max(64 instructions, 5% of block cost)`
as its tolerance. This gate does not establish an all-input guarantee.

## 1. Nested loops need an interaction

```c
for (long i = 0; i < n; ++i)
    for (long j = 0; j < m; ++j)
        s += heavy(j + 1);
```

Declaring `n,m` asks for `a*n + b*m + c`. Independent variation of both inputs
exposes the missing product. Declare `n,m,n*m`, and the checker finds:

```text
cost = 5*n + 0*m + 106*(n*m) + 23
```

The outer-loop overhead still depends on `n`. Declaring only the total inner
iterations can leave that overhead unexplained. All products here fit int64;
an annotation intended for larger domains would also need overflow handling.

## 2. Branches belong in PCV expressions

```c
for (long i = 0; i < x; ++i)
    s += i < y ? heavy(i + 1) : light(i + 1);
```

On the tested positive inputs, neither `x` nor `y` alone says how many times
each branch runs. These entry-time expressions do:

```c
heavy_iters = x < y ? x : y;
light_iters = x > y ? x - y : 0;
```

The discovered interface is:

```text
cost = 109*heavy_iters + 11*light_iters + 21
```

This is affine in the declared PCVs, even though the PCVs are piecewise functions
of the inputs. If negative `y` were allowed, the first expression would need
`max(0,min(x,y))`; the domain matters.

## 3. Averaging can hide the missing variable

```c
for (long i = 0; i < n; ++i)
    s += mask[i] ? heavy(i + 1) : light(i + 1);
```

For every `n`, the workload supplies three masks: none, half, and all of the
entries take the expensive branch. With only `n` declared, drperf averages all
nine calls at that state, including the repetitions. It reports a perfect fit:

```text
mean_cost = 60*n + 21
```

Separate measurements of the same kernel and call site show:

```text
all light: 11*n + 21
all heavy: 109*n + 21
```

The mean is correct for this test distribution. It is not an explanation of
each execution. A different branch ratio changes the mean, and a constant
ratio across lengths can conceal this dependence completely.

Repair: declare `heavy_iters` and `light_iters`. The formula becomes the same
`109*heavy_iters + 11*light_iters + 21` as above. A checker improvement would
retain per-invocation cost variation before aggregation and flag states whose
executions differ substantially. This suite demonstrates the issue with
separate homogeneous measurements; it does not implement that improvement.

The synthetic producer already knows the mask's population count. Without
such metadata, computing this PCV requires an O(n) scan. That is a real
annotation cost, even when done outside the marked region. Maintaining a
summary while constructing/updating the data can avoid the extra scan. Counting
actual branches after execution instead would not be an entry-time predictor.

## 4. Correlated inputs do not identify the right PCV

```c
/* n is an input, but this kernel does not use it. */
for (long i = 0; i < m; ++i)
    s += heavy(i + 1);
```

Training on `m=n` while declaring `n` produces `106*n + 20`, with zero
unexplained cost. Declaring both variables on that same diagonal does not
resolve the ambiguity: the checker reports a dependent column.

The validator freezes the trained formula, then compares it against measured
costs on an independent `n,m` grid. It fails badly. Declaring `m` instead gives
`106*m + 20` on that grid.

There is another trap: keeping only `n` as the key while sweeping the same
set of `m` values for every `n` produces a perfect *constant mean*, 49,628
instructions. Input diversity alone does not help if aggregation erases it.
Use independently varied candidate state, retain within-state variation, and
validate frozen predictions. Full column rank removes coefficient ambiguity
on the sample; it does not prove that the feature set is complete.

## 5. Small inputs cannot reveal an unexecuted path

```c
if (n <= 64)
    return linear_work(n);
return nested_work(n, n);
```

Inputs 8,16,32,48,64 produce `106*n + 26`, with zero unexplained cost.
The validator freezes that formula before comparing against measured counts
at 96,128,192,256. Its relative error exceeds 98% at each larger input.

Once both paths are exercised, declaring only `n` leaves substantial work
unexplained. The repair declares:

```c
small_n         = n <= 64 ? n : 0;
large_n         = n > 64 ? n : 0;
large_n_squared = n > 64 ? n*n : 0;
large_path      = n > 64;
```

The discovered interface is:

```text
cost = 106*small_n + 5*large_n + 106*large_n_squared + 2*large_path + 26
```

The indicator captures fixed overhead that differs between paths. This uses
four PCVs; the marker now retains all declared PCVs with dynamic storage. In a larger example, separate
path-specific regions can reduce the number needed, provided their costs are
accounted for explicitly; nested marked work must not silently disappear.

These are designed counterexamples, not a blind demonstration of model
discovery. The repaired annotation has seen both paths. Small-case symbolic
insight is useful when tests exercise the relevant behaviors; it cannot
guarantee a prediction about unseen paths without additional reasoning or proof.

## 6. Zero unexplained cost does not mean zero error

```c
uint64_t s = 0;
if (x == 2)
    for (int i = 0; i < 16; ++i) {
        s += i;
        KEEP(s);  // compiler barrier preserves this tiny loop
    }
```

For `x=0,1,2,3,4`, declaring only `x` produces the constant formula 30.2
instructions. Every block fits within the current absolute tolerance, so the
unexplained part is zero. Actual cost is 17 instructions without the branch
and 83 with it: up to 77.65% relative prediction error.

Declare `x` and `takes_branch=(x==2)`, and the checker finds exactly:

```text
cost = 17 + 66*takes_branch
```

Independently of this annotation repair, the checker should expose a numerical
reconstruction check:

```text
error = abs(formula(PCVs) + reported_unexplained - measured_cost)
```

An application can require both low unexplained share and sufficiently small
reconstruction error. Per-block tolerance is not automatically a region-level
relative error bound. This validator checks both; core drperf is unchanged.

## What this suggests for the calculus and agent workflow

The useful restriction is the affine combination of PCVs. The PCVs themselves
can contain multiplication, conditions, or data summaries. For the current
blockwise checker, they must explain the individual basic-block counts;
expressing only the sum of all block costs is a weaker requirement.

A general program-valued PCV can reproduce the entire execution and return its
cost. That makes expressibility trivial while making the interface expensive.
Track two separate obligations: whether the interface explains cost, and how
much computation/information its PCVs require. These examples use O(1)
expressions or producer metadata; they do not establish that an inexpensive
PCV always exists for arbitrary programs.

For agents, the examples suggest this sequence:

1. State the input domain and choose cheap candidate PCVs.
2. Exercise independent dimensions and both sides of relevant branch boundaries.
3. Inspect unexplained work, dependent columns, and within-state variation.
4. Add interactions, conditional counts, or maintained summaries as justified.
5. Check numerical reconstruction separately, then test frozen predictions.
6. Only then use the interface to guide optimization and measure its result.

All guarantees here concern measured user-space instruction counts on exercised
states. Elapsed time, cache latency, kernel work, and GPU work require suitable
additional measurements. A Lean proof over program semantics would be a
different, stronger guarantee than accepting these observed fits.
