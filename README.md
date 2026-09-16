# drperf

Cheap perf interface generation for coding changes.

Exact instruction counts for marked regions of a program, turned into a cost
function of the state you declare, plus the relations between those states
across regions, from one run.

DynamoRIO-based, so the counts cover everything the region executes:
interpreter, allocator, C/Rust/C++ extensions, worker threads.

## Use

```
./build.sh                 # DynamoRIO 11.3.0, marker library, client, examples
bin/drperf ./myapp         # or: bin/drperf python app.py
```

```
cost per call, in instructions

  handle = 1,336.7*q + 363.4   (inflight: no effect; 12% of the cost follows no declared state)
      q: 504.7 parse [base], 287 __printf_buffer [libc.so.6], 95 __printf_buffer_write [libc.so.6]
      constant: 170.8 parse [base], 81.5 __memcpy_avx_unaligned_erms [libc.so.6]
      unexplained: 2,053.1 parse [base]
  ingest = 152*batch + 16   (bytes: moved in step with batch)
      batch: 152 ingest [base]
      constant: 11 ingest [base], 2 _init [base], 2 perfmark_end [libperfmark.so]
  parse  = 5*len + 487   (entries: did not vary)
      len: 5 parse [base]
      constant: 482 parse [base]

relations

  handle.inflight = cum(ingest.batch) - cum(handle.q)   (holds at all 57 calls)
```

Each term is broken down into the functions it comes from, largest first, so a
coefficient that moves points at the code that moved it.

That is the whole interface: `drperf` followed by the command you would have
run anyway. No options.

[Source-region benchmarks](benchmarks/README.md) collect vLLM, Wan, V8 RegExp,
JavaScript runtime and accidental-quadratic cases. Each target has pinned source
and an empty marker, ready for PCV discovery. Historical evidence and future
evaluation designs are kept alongside the collection.

[Runnable synthetic counterexamples](examples/drperf_limits/README.md) show six
ways a performance interface can fail or appear misleadingly successful, with
repaired PCVs and checks against actual drperf measurements.

Start with `examples/playground`, a 250-line C system with three regions and a
one-line change to measure. `SPEC.md` states exactly what is computed, on one
page.

## Markers

You declare a region and the integers that matter to it. Nothing else is added
to the program. Up to four declared states per region; all of them form the key
and the formula is derived in all of them.

```c
#include "perfmark.h"
perfmark_begin("parse", "len", n);
...
perfmark_end("parse");

const char *names[2] = { "q", "inflight" };
int64_t vals[2] = { q, inflight };
perfmark_begin_v("handle", 2, names, vals);
```

```python
import perfmark
with perfmark.region("schedule", running=len(self.running), waiting=len(self.waiting)):
    ...
```

```rust
let _r = perfmark::Region::new_v("handle", &[("q", q), ("inflight", inflight)]);
```

Outside DynamoRIO the markers are empty functions, one call each.

## Reading the output

- A state gets a coefficient only if it varied during the run. Otherwise the
  line says why it has none: it never varied, it moved in step with another
  state, or the cost did not follow it.
- Cost that follows no declared state is reported as a percentage and left out
  of the formula, never smeared into a coefficient. It is broken down by
  function too, under `unexplained`.
- A region keeps at most 128 distinct state combinations, and the counter
  arrays are bounded in address space. Calls beyond either limit are reported
  as not modelled rather than merged into a state point they do not belong to.
  A state with very many values (a monotonically growing counter, say) will hit
  this; declare something coarser.
- When the run itself was not clean, the tool says so on stderr before printing
  anything: basic blocks that did not fit the counter table, state combinations
  that got no counters, states dropped at the marker, unmatched region ends, a
  truncated trigger trace. Formulas printed after such a warning are fiction.
- `cum(R.s)`, `last(R.s)`, `count(R)` and `cumend(R.s)` are counters over the
  triggers that began (or ended) before the one being explained. A relation is
  reported only if it holds exactly at every trigger, in integer arithmetic.
- A region's cost is its own. Regions nested inside it are excluded and named
  with their calls per trigger (`excludes parse x10.5`), so you can compose
  them yourself; they are not folded in, because the client aggregates a nested
  region over every parent that called it.

## Turning the markers off

Markers are cheap but not free: in Python a `with region(...)` costs about
1,459 ns per entry through a `@contextmanager` shim and 378 ns through the
cheapest class-based one, because the statement still runs. `bin/perfmark-regions`
removes the statement instead of making it cheaper.

```
bin/perfmark-regions status src   # how many markers are live
bin/perfmark-regions check  src   # prove off -> on reproduces every file
bin/perfmark-regions off    src   # header commented, body dedented
bin/perfmark-regions on     src   # sources restored byte for byte
```

`off` rewrites

    with region("name", n=len(x)):
        body

into

    # perfmark:off with region("name", n=len(x)):
    body
    # perfmark:end

The end sentinel is what makes `on` unambiguous, multi-line headers keep their
continuation indentation, and imports left unused by the transform are found by
running ruff and given a tagged `# noqa` that `on` strips again, so nothing is
deleted. It refuses, and reports, two cases rather than guessing: a `with` that
holds another context manager beside the region, and a body containing a
multi-line string, where dedenting would rewrite the string itself.

In C and Rust this is unnecessary: the markers are empty functions outside
DynamoRIO, and the Rust ones vanish entirely behind a cargo feature.

## Late attach

DynamoRIO starts at the first marked region, not at process start, so imports,
model loading and warm-up run natively and are never translated. A small
preloaded library (`build/libdrperf_attach.so`) reserves DynamoRIO's address
space, and the marker library starts it at the first region. Threads that
already exist are taken over.

For vLLM this is the difference between 280 seconds and 26 (12 native), because
almost all of that run is PyTorch and vLLM startup that no region covers.

## Measured

| check | result |
|---|---|
| C loop, 3 repeats (`tests/ctest.c`) | 4 instrs/iteration exactly, identical |
| 4 workers under the main thread's region (`tests/cthreads.c`) | 4 x 400,006 attributed to `loop_work`, exact |
| marker path, 32 threads x 200K begin/end pairs | 4.2 µs per pair per thread |
| C / Rust / C++ suites (`examples/{c,rust,cpp}_suite`, 27 cases) | exact `a*n + d` with 0 irregular on every exactly-affine case (loops, nested regions, rep-string, pthreads, scoped threads, OpenMP with waiting excluded, virtual and template calls); a delta of +3 instructions per iteration recovered exactly; prediction 8x beyond the profiled range within 0.0%; byte-identical block dumps across repeats |
| negative controls | `n^2`, hash-table rehashing and an independent undeclared variable are reported as irregular, not fitted; `n log n` over a fourfold range passes as a line with a negative constant, which is flagged |
| two declared states, C (`c9_twovar`) | `4*n + 5*m + 29` exact, coefficients attributed to the two loops; the product `n*m` comes out 98.9% irregular |
| two declared states, Python (`examples/py_twovar`) | `1,028*n + 1,280*m`, 1.8% irregular, although both loops run in the same interpreter blocks |
| queue invariant, 2 threads | `q = cum(produce.m) - cum(consume.q)` learned exactly, in C, Rust and Python |
| vLLM `execute_model` (decode regime, all threads) | `172,749,376*num_tokens + 12,515,892`, 1.2% irregular; predicts a larger run's decode steps within 1.4% |
| vLLM slowdown | 25.7 s profiled vs 12.1 s native (2.1x); 41 s including analysis |

## Layout

```
perfmark/           perfmark.h/.c -> build/libperfmark.so; attach.c -> build/libdrperf_attach.so
  python/           perfmark.py (binding), _perfmark.c (C fast path)
  rust/             perfmark crate
client/drperf.c     DynamoRIO client -> build/libdrperf.so
lib/runner.py       running the program and reading back what the client wrote
lib/derive.py       cost formulas from per-basic-block counts
bin/drperf          the tool
SPEC.md             what is computed, formally, and what is not
examples/           playground (start here), c/rust/cpp suites, queue, py_delta, py_twovar,
                    torch_delta, rust_delta, vllm_cpu
tests/              ctest.c (exactness), cthreads.c (attribution), cmarkers.c (marker throughput)
third_party/        get_dynamorio.sh (pinned sha256); vllm-cpu/setup.sh
```

## How counting works

Every basic block gets two inline adds: the thread's total and the current
region's per-block counter, a pointer swapped by the markers. Regions are keyed
by (region, declared states, root region) and aggregated per thread, merged at
exit. Threads with no open region of their own count into the innermost region
of the leader, each with a private counter array, so counts stay exact under
concurrency. The marker path takes no lock. `rep movs/stos` are expanded so
each iteration counts one instruction. A region keeps at most 128 distinct
state combinations, which bounds memory when a declared state has many values.

## Caveats

- Instructions are not time. A change that removes instructions but adds cache
  misses passes; one that vectorizes and adds instructions looks worse.
- Counts are exact and reproducible for deterministic single-threaded programs.
  With OpenMP the partition of work varies between runs; the total usually does
  not, and runtime spin-waiting is excluded and reported separately.
- A marker pair costs a few hundred instructions. A region of a few lines is
  fine; a region inside a hot inner loop measures itself.
- A formula needs at least (variables + 2) different state points in the run.
- The numbers describe these binaries on this CPU. A toolchain or machine
  change invalidates a baseline.
- Kernel time is not counted; syscalls per region are reported as the hint.
- The runner pins `PYTHONHASHSEED=0` and, unless you set them yourself,
  `OMP_NUM_THREADS`, `MKL_NUM_THREADS` and `OPENBLAS_NUM_THREADS` to 4, so runs
  are comparable. An application that chooses its own thread count ignores
  this. Set them in the environment to override.
- DynamoRIO 11.3.0 crashes in `dr_get_proc_address` on some torch libraries, so
  markers are looked up only in modules named `*perfmark*` and the main
  executable; module names come from file names because SONAME parsing is wrong
  for those libraries.
