# drperf: interactive performance-interface discovery

**A checker for lightweight performance interfaces, built to help coding agents
understand and improve the cost of their code.**

An agent already has an implicit cost model when it writes or optimizes code.
That model can drift from reality, especially across library calls. drperf makes
the model explicit: the human or agent annotates a region with the expressions
it believes the cost depends on—its **performance-critical variables (PCVs)**—and
drperf checks how much of the observed execution those PCVs explain.

The interactive part is the discovery. The annotator proposes the vocabulary;
the checker supplies coefficients and feedback. The analogy to interactive
theorem proving is this division of work, not an all-input proof of performance.
drperf is an experimental execution-based checker.

## Explain first, then optimize

1. **State the cost model.** Mark the region and declare its PCVs. Coefficients
   are inferred; the annotator does not supply them.
2. **Explain the observed cost.** Run small tests that vary the PCVs, inspect
   the unexplained functions, and refine the annotation: add a variable, change
   an expression, or split a region. Check reconstruction error and variation
   between inputs as well as the unexplained share.
3. **Optimize the explained work.** Investigate an unexpectedly large
   coefficient or a dependency that should not exist. Change the code, check
   correctness, and compare the same workload and region boundaries again.

For example, a lookup that unexpectedly copies its whole map has a cost that
grows with map size. Naming that dependency explains the surprise; removing
the copy removes the corresponding work. Explanation and optimization are
separate steps: a good fit can describe inefficient code perfectly.

PCVs are expressions, not just existing variables. A nested loop may need
`n*m`; a conditional path may need `n if enabled else 0`; a tree lookup may need
counts of different comparisons. The final formula is affine in the declared
PCVs, so the annotator supplies the nonlinear or conditional structure:

```python
with perfmark.region("pair_scan", pairs=len(left) * len(right)):
    for a in left:
        for b in right:
            inspect_pair(a, b)
```

## What the checker computes

DynamoRIO counts user-space CPU instructions executed inside each region,
including interpreter, allocator, native extensions, and attributed worker
threads. The marker records PCV values at entry. For each executed basic block,
drperf fits a joint affine formula over all declared PCVs:

```text
block instruction cost = a1*PCV1 + ... + ak*PCVk + d
```

A block is accepted only when the fit is within tolerance at every observed
state. Accepted blocks contribute to the region formula; rejected blocks form
the unexplained part, tabulated by state and broken down by function:

```text
observed cost is modeled as A*PCVs + Constant + unexplained
```

**Lightweight** means the interface describes only the supplied PCVs at the
states exercised by the tests. It does not prove a bound over all inputs.
Small cases can reveal a repeated copy, a quadratic term, or redundant work
without first running a large workload. Predicting the benefit at larger sizes
is a separate hypothesis to validate.

The current collector fits **mean block counts for calls sharing a PCV state**.
Exact counting therefore does not imply that every individual call is explained:
averaging can hide a missing variable, and per-block tolerances do not guarantee
a small relative error in the final formula. The
[hash-table study](examples/hash_table_cost/README.md) reproduces both issues.
These are active checker limitations. See [SPEC.md](SPEC.md) for the mechanics.

## Findings in Wan video generation

The [full-model GX experiment](examples/wan_gx/README.md) runs the official
pretrained Wan2.1-T2V-1.3B pipeline through text encoding, 81-frame / 50-step
denoising and VAE decode. It repairs CPU/GPU control-metadata boundaries,
marks 25 CPU regions, and removes repeated model transfers, rotary construction,
prompt/K/V projections, and packing/concatenation work. GX skips device
computation: these runs assess host work, not video correctness or GPU latency.
With the same measurement boundary, recorded marked CPU instructions fell
from 23.63 billion to 18.94 billion in the first pass, then to **14.39 billion
(39.12% below baseline)** after further attention metadata, layout, convolution
and dispatch changes. See the [latest results and limitations](examples/wan_gx/MORE_RESULTS.md)
and the [first comparison](examples/wan_gx/RESULTS.md).

A [native A100 PCIe 40GB follow-up](examples/wan_gx/NATIVE_RESULTS.md) measured
**218.88 s baseline versus 207.43 s optimized (5.23% lower generation latency)**
for one matched 81-frame / 50-step pair, including text encoding and VAE decode,
excluding model loading. Both outputs are finite, but their final latent
relative L2 difference is 3.15%; numerical/perceptual equivalence has not been
established. This is a measured latency result, not yet a validated equivalent
replacement.

A [GX/GXVM timing case study](examples/wan_gx/TIMING_STUDY.md) holds all
359,473 GPU launches/BLAS operations fixed. Trace-guided drperf work removed
redundant model-residency walks and precision scopes: marked CPU instructions
fell **15.39%**, while one paired simulation measured **195.75 -> 195.03 s
(0.37% lower)**. Stream gaps fell from 0.77 s to 0.05 s; GPU work dominates the
remaining time. The study includes checked launch sequences and reusable
profiling inputs. GX skips GPU arithmetic; these are experimental simulated
timings with CPU-profile limitations, not a hardware speedup claim.

Small CPU executions of real Diffusers code exposed work that an agent could
inspect and remove. The historical experiments used tiny, randomly initialized
Wan models; the newer region benchmarks use bounded CPU fixtures. These counts
include CPU tensor kernels and are not measurements of GPU kernel execution.

| Finding | Change and recorded evidence |
| --- | --- |
| Rotary tables rebuilt each transformer forward | Cache by shape/device/dtype; historical mean region instructions fell 87.9%. [Record and corrections](benchmarks/cases/wan_a/reference/record.md) |
| Fixed prompt projected repeatedly | Cache the text projection and per-layer cross-attention K/V; the historical cross-attention projection region fell from 378,712 to 137,932 instructions. [Record](benchmarks/cases/wan_c/reference/record.md) |
| Text-encoder work follows padded length and its square | Encode a shorter padded sequence, then restore the output shape; a tiny CPU case with 32 real tokens and a 512-token budget used 45.5x fewer region instructions. GPU output digests differ; this is not a general equivalence claim. [Record](benchmarks/cases/wan_d/reference/record.md) |
| VAE repeatedly concatenates a growing output | Collect chunks and concatenate once. The quadratic copying is real, but the original attribution of rising per-frame cost was corrected: different first/later chunk work explained most of that trend. [Record and correction](benchmarks/cases/wan_a/reference/record.md) |
| VAE blend loops dispatch tensor operations per row/column | Broadcast the blend for nonoverlapping extents greater than one; recent tiny CPU workloads used 23.07% / 23.54% fewer region instructions. The optimized fits still fail the 5% unexplained gate. [Patches and results](bench_optimized/wan/README.md) |

**The archive also reports a real GPU follow-up, with no meaningful end-to-end
speedup.** On an A100-SXM4-80GB with Wan2.1-T2V-1.3B in bfloat16, the 81-frame,
30-step run took 98.831 s pristine, 98.897 s with the earlier fixes except T5,
and 98.992 s with all earlier fixes. The non-T5 variant retained the baseline
latent digest; the T5 padding change did not. This historical run is separate
from the recent CPU blend experiments and has not been rerun for this README.
See [the GPU follow-up](benchmarks/evaluator/evidence/CASES.md#the-wan-fixes-on-a-real-gpu-no-wall-clock-change-and-why-that-is-the-honest-answer).

The useful result is discovering unnecessary work from small executions.
Whether removing it reduces latency depends on the actual execution path and
bottleneck. drperf counts CPU instructions; GPU correctness, device timings,
memory use, and end-to-end speedups need their own measurements.

The [causal-video study](examples/causal_video/README.md) extends this workflow to
pretrained Inferix and FastVideo Self-Forcing models, with A100 kernel databases,
GX `partial_sync`, and separate drperf measurements. A [native Inferix
comparison](examples/causal_video/NATIVE_RESULTS.md) reduces median latency from
41.29 to 12.65 seconds with identical saved output. A separate
[drperf-guided RoPE cache](examples/causal_video/CPU_RESULTS.md) reduces marked
CPU instructions by 5.2% but yields no additional native latency improvement.
The [FastVideo comparison](examples/causal_video/FASTVIDEO_NATIVE_RESULTS.md)
finds no convincing latency gain from keeping DiT weights resident; the study
includes both [native kernel databases](examples/causal_video/evidence/kernel-databases/README.md).

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
run anyway. Optional environment controls can narrow the measurement scope:

```
DRPERF_EXCLUDE_CUDA_MODULE=gx_cuda.so DRPERF_FOLLOW_THREADS=0 bin/drperf python app.py
```

`DRPERF_EXCLUDE_CUDA_MODULE` selects one module basename. Its instructions and
synchronous callees beneath exported CUDA driver/runtime and GPU-library APIs
(cuBLAS, cuDNN, cuSOLVER, cuSPARSE, cuFFT, cuRAND, cuTENSOR) are excluded.
`DRPERF_FOLLOW_THREADS=0` prevents unmarked threads from inheriting the leader's
region; explicitly marked worker regions still count. Both are opt-in; default
measurement retains worker attribution and excludes no CUDA module. Raw output
records the scope and exclusion counters; an unmatched exclusion is invalid.
Asynchronous work outside that module is not excluded by a call-stack boundary.

[Source-region benchmarks](benchmarks/README.md) collect 1,000 regions from
vLLM, Wan, V8 RegExp, JavaScript runtimes, compilers, and libraries, including
accidental-quadratic cases. Each target has pinned source, an empty marker, and
test support, ready for PCV discovery. The planned evaluation compares agents
with and without drperf feedback, including whether small cases expose growth
that timing alone misses. The collection is not a completed agent-accuracy study.
Browse [annotated regions, successful cases first](bench_anontated/review/annotated-regions.md),
[experiment results](bench_anontated/RESULTS.md), and
[optimization copies](bench_optimized/README.md).

[Runnable synthetic counterexamples](examples/drperf_limits/README.md) show six
ways a performance interface can fail or appear misleadingly successful, with
repaired PCVs and checks against actual drperf measurements.
The [B-tree branch study](examples/btree_branches/README.md) examines real Python
BTrees lookups and separates semantic expressibility from limitations of the
current blockwise checker.
The [hash-table study](examples/hash_table_cost/README.md) tests real CPython
dictionary collisions, costly equality callbacks, and resizing, including
cases where fitting state averages hides large differences between inputs.

Start with `examples/playground`, a 250-line C system with three regions and a
one-line change to measure. `SPEC.md` states exactly what is computed, on one
page.

## Markers

You declare a region and the integers that matter to it. Nothing else is added
to the program. Every declared integer state forms part of the key, and the
formula is derived in all of them. PCV storage is dynamically sized in the
client and bindings; there is no fixed four-PCV limit. Fitting k PCVs still
needs at least max(3, k+2) distinct observed states, within the existing
128-state-per-region measurement budget.

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
- Blocks whose observed state means fail the affine check are reported under
  `unexplained`, as a percentage and by function. An omitted variable can still
  hide in a coefficient or constant if it is correlated with a PCV or averaged
  into the state means. Low unexplained cost alone is not proof of completeness.
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
| negative controls | sufficiently curved counts such as `n^2` fail the observed-point tolerance; curves such as `n log n` can pass over a limited range. A negative constant alone is not evidence of curvature |
| two declared states, C (`c9_twovar`) | `4*n + 5*m + 29` exact, coefficients attributed to the two loops; the product `n*m` comes out 98.9% irregular |
| two declared states, Python (`examples/py_twovar`) | `1,028*n + 1,280*m`, 1.8% irregular, although both loops run in the same interpreter blocks |
| queue invariant, 2 threads | `q = cum(produce.m) - cum(consume.q)` learned exactly, in C, Rust and Python |
| vLLM `execute_model` (decode regime, all threads) | `172,749,376*num_tokens + 12,515,892`, 1.2% irregular; predicts a larger run's decode steps within 1.4% |
| vLLM slowdown | 25.7 s profiled vs 12.1 s native (2.1x); 41 s including analysis |

Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` after building
for affine-acceptance and end-to-end marker regressions, including 64 PCVs
through C, Rust, Python's native extension, and the ctypes fallback. The
[B-tree regression](examples/btree_branches/README.md) checks six PCVs through
the normal marker at depths 2–8.

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
- GPU kernels are not instrumented. A CPU fixture can reveal source-level
  redundant work, but its instruction coefficients do not transfer to GPU
  execution. The separate native Wan comparisons above measure latency and
  numerical differences directly; CPU savings alone establish neither.
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
