# Declared wait checking

Status: working opt-in prototype. Motivation: `lm_cache_task.md`.

The human or agent declares publication and completed-wait checkpoints inside
ordinary regions. Drperf checks those declarations against captured execution
and requested publication-delay probes. The original code supplies the wait and
its condition; annotations do not add synchronization. The practical
[publish/waited usage guide](docs/waited.md) covers placement in callers of
shared synchronization helpers. Start with
[declared event checkpoints](#declared-cpugpu-event-checkpoints-and-delayed-publication-probes).
Native API observations provide supporting evidence and flag unexplained waits;
they do not replace the declared event model.

A semantic wait is an operation that requires a completion or a resource before
it can proceed. It remains a wait operation when the requirement is already
satisfied. Lock acquisition is reported separately: observing a lock call alone
does not establish contention. Ordinary region nesting/order does not create
wait edges. A stream sync can depend on several submitted operations; this does
not imply that every region waits on every other region.

## Native evidence for unexplained waits

This supporting capture uses existing `perfmark` regions and PCVs; it needs no
additional `kind="wait"` or `on=` annotation.
DynamoRIO observes supported synchronization APIs, their object identities,
arguments, returns, and the active region invocation. The exporter discovers
candidate endpoints and derives exact affine **operation counts per invocation**
over the parent's PCVs, including calls with zero operations.

```
consume(items): sem_wait calls = items
consume waits on completion published by decode
metadata: pthread_mutex_lock calls = 1; ownership unresolved
```

This is a separate interface beside CPU work. It is not a latency prediction.
A host submission region finishing does not mean its device work finished.

## What is implemented

- libc semaphore wait/post/init/destroy, mutex acquisition/release,
  condition wait/signal/broadcast, thread join, and socket receive wrappers;
- selected CUDA runtime event/stream synchronization, event recording,
  stream creation/destruction, and async-copy submission wrappers;
- region invocation IDs, process/thread IDs, object handles, API entry/return
  order, return status, instrumented elapsed time, and potentially blocking
  syscall attempts inside an observed API;
- detailed API observations inside application regions; unmarked libc lock,
  condition, join and receive housekeeping is aggregated by API to avoid filling
  the event budget before useful regions run. Semaphore and CUDA object history
  is retained outside regions too, to connect earlier publications to later waits;
- `.waits` raw sidecars, a `waits` section in exported JSON, and CLI output;
- bounded collection: 100,000 API calls per process by default; set
  `DRPERF_MAX_WAIT_RECORDS` (up to 10,000,000) for larger workloads.
  Dropped/missing observations
  are reported and disable dependency matching and count-formula claims.

Dependency matching is deliberately limited:

1. A process-local, zero-initialized semaphore with a closed, observed lifetime
   and exactly one successful post and consumption links the consumer to the
   publication's region invocation. Initial tokens, multiple token sources,
   shared-process semaphores, or missing history remain unresolved.
2. A CUDA event wait or queued stream-event dependency with an observed, non-IPC creation can match the most recent
   observed event-record generation.
   A concurrent record or observed handle destruction/recreation prevents an
   old record from being reused. This identifies captured stream work, not CPU
   completion of the recording region. A queued stream dependency does not block
   the host. Cross-process CUDA IPC is not supported.
3. An explicit CUDA stream sync links to observed async-copy submissions on the
   same stream since its preceding completed sync/create. This is a **partial**
   dependency list: kernels and imported event dependencies are not yet traced.
   Default/legacy/per-thread stream handles are left unresolved.
4. Mutex, condition, join, socket and device-wide sync operations
   are visible even when their producer/owner is unresolved. A condition signal
   is not automatically treated as satisfying the application's predicate.

No operation is labelled `blocked` merely because a syscall occurred, or `spun`
because a small loop repeated. Elapsed time and futex/poll/receive attempts are
supporting observations; physical blocking remains `unknown` in this prototype
(queued stream-event operations are explicitly not host waits).
Matched dependencies are evidence within captured API coverage, not a proof for
unobserved implementations or executions.

## Delay probes

```
DRPERF_WAITS=1 \
DRPERF_WAIT_DELAY_REGION=decode DRPERF_WAIT_DELAY_MS=100 \
  bin/drperf ./program
```

The first intervention delays `sem_post` in the named ordinary region before
publishing the token. It does not require a wait annotation. Fixed delays do not
guarantee the consumer reaches its wait: inspect the recorded ordering. Tests
check that a delayed publication can overlap a consumer's wait without losing
the object-based producer link. This tests one schedule, not all schedules.

Delay runs are marked `probe` and must stay separate from baseline cost fits:
interventions can change application spinning, scheduling, and other costs.
The sleep itself is client work, not measured application instructions.

Important implementation detail: keep `DRWRAP_NO_FRILLS`. General drwrap mode
holds its shared wrap lock while invoking callbacks; sleeping in that callback
also stalls other wrappers and invalidates this experiment. CUDA instruction
exclusion is multiplexed into the same callback, preserving one wrapper per
address while keeping synchronization observation enabled.

## Run the example

```bash
cd /home/ubuntu/drperf
cmake --build client/build -j 4
python3 examples/waits/run.py
python3 -m unittest discover -s tests -p test_waits.py
```

`examples/waits/demo.c` has ordinary `consume`, `decode`, and `metadata` regions.
It contains no wait/dependency annotations. The runner refreshes only its own
raw outputs under `out/waits/{baseline,delayed}` and writes:

- `out/waits/baseline.drperf.json`
- `out/waits/delayed.drperf.json`

The baseline normally observes publication before consumption; the delay probe
exposes overlap and futex-wait attempts. Both learn `consume -> decode`, and both
fit `sem_wait calls = items`. Mutex acquisition is reported independently.

For another workload, enable `DRPERF_WAITS=1` in the environment that actually
runs drperf. Use `DRPERF_REPORT=/path/report.drperf.json` to retain the portable
report. Containers/remote copies need the updated client and Python exporter.
Captures without synchronization events need a fresh execution. Re-exporting
old counters cannot reconstruct them. Use the CLI output or JSON for detailed
native API evidence.

## Limits and next experiments

The prototype wraps selected APIs, not every way to wait. Custom atomic loops,
raw syscall call sites, direct CUDA driver APIs, opaque native GX internals,
remote request matching, and full GPU kernel dependencies remain unsupported.
Late attachment misses earlier publications/initialization; those dependencies
must remain unresolved. Source attribution currently identifies the enclosing
region, not the exact Python line of an unannotated call.

Instruction exclusion and synchronization observation are separate. The native
CUDA test uses a fake runtime to verify event generations and continued wait
observation inside excluded calls; it is not GPU timing validation. Under GX,
reported synchronization describes emulated execution, not actual GPU latency.

## Region execution graphs

```bash
bin/drperf-graph profile.drperf.json -o graph.html
bin/drperf-graph profile.drperf.json -o paths.html \
  --root rt.submit_store --root rt.submit_load --root rt.poll --depth 1 --all-roots
```

The self-contained HTML shows only regions. Click a node for its exclusive CPU
cost formula, PCVs, source locations, and observed wait operations. Displayed
coefficients are rounded to integers; the embedded profile values retain precision.
`--depth 1 --all-roots` opens compact views of direct children, with an
"Explore this region" button to navigate deeper and Back to return.

- Solid edges: observed consecutive direct children of the same invocation,
  or consecutive outer regions in the same execution context. They do not prove
  a required dependency and may have unmarked work between them.
- Dotted edges: nesting. Each invocation's exclusive cost is counted once,
  independently of its number of incident edges.
- Blue dashed edges: the source waits on work published by the target region.
  These refer to synchronization within invocations, not whole-region
  return-before-entry. No all-to-all waiting is assumed.

Counts are fitted against the enclosing region's PCVs, including invocations
with zero occurrences. Execution contexts are used internally to establish order;
threads are not graph nodes. Collapsed region graphs can have cycles from
repeated calls and do not establish a critical path or total request latency.
Unresolved producers remain visible on nodes. Incomplete traces cannot produce
an execution graph; partial synchronization coverage cannot produce wait edges.

For Ditto's in-process GX workload, `exp/gx_kimi/drperf_serve.py` forwards
`DRPERF_WAITS=1`. The workload harness attaches after vLLM imports but before
engine construction when that flag is enabled. Attaching only after warm-up
misses persistent CUDA event creation and prevents safe matching of later DMA
waits. This bootstrap marker is internal, not a wait annotation in Ditto code.
The Qwen workload uses `DRPERF_MAX_WAIT_RECORDS=500000` to retain initialization
history as well as the measured region operations.

### Ditto capture

Applied to the staged Ditto Qwen2.5-0.5B workload under GX functional emulation,
with dummy weights and `DITTO_FRAMEWORK_TEST=1` (GPU launches with simulated
codec output; device arithmetic is not validated). Six sessions and two turns
exercise store, reload, and compaction. No wait annotations were added to Ditto.

Artifacts on this workspace:

- Graph: `/home/ubuntu/compression/ditto_kv/example/qwen2.5B/ditto.graph.html`.
- Profile, raw records and exact source snapshot:
  `/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/`.

The final capture retained 118,113 synchronization API records with no drops.
It resolves nine `store.drain -> carrier.transfer` edges at invocation level:
each drain synchronizes the CUDA event generation recorded by its transfer.
The aggregated count is one synchronization per observed drain. This is a
dependency on submitted device work, not a claim that the entire producer's CPU
region must finish before the consumer enters. Internal stream dependencies are
also visible; unresolved lock owners remain unresolved. The graph establishes
neither GPU latency nor contention from these observations.

### Source audit of the Ditto graph

See [the manual Ditto wait audit](examples/explorer/DITTO_WAIT_AUDIT.md). All five
matched region-pair links have event/source support, but readiness polling is
missing and event-record attribution is not full producer-work provenance.
The graph is not a complete semantic wait model.

### Checking agent-declared indicators on Ditto

`bin/drperf-check-waits` checks a separate declaration file against an existing
profile. It does not alter annotations, fit new PCVs, rerun GX, or install CUDA
wrappers. The first example is
[examples/waits/ditto_contracts.json](examples/waits/ditto_contracts.json):

```json
{
  "version": 1,
  "claims": [{
    "id": "transfer-orders-after-compute",
    "region": "carrier.transfer",
    "api": "cudaStreamWaitEvent",
    "indicator": "d2h == 1",
    "producer": "carrier.transfer"
  }]
}
```

This describes `I_{d2h == 1} * Wait[carrier.transfer]`. Here the producer is
specifically the region that **records the completion event**; it does not
claim that the compute work preceding that event originated in this region.
Set `producer` to `null` when unknown; the obligation stays unverified.

The checker checks every invocation, including those with no synchronization:

- indicator 0, observed synchronization: unexpected presence / omitted wait;
- indicator 1, no synchronization: unexpected absence / incorrect indicator;
- matched publication in a different region: incorrect producer;
- missing/ambiguous publication or unsupported ownership: unverified producer;
- synchronization without a declaration: `unexplained(Wait[?])`, or an observed
  publisher name when available.

Checking is per invocation, not per-state averages. The indicator predicts
whether an operation occurs; the checker separately fits its multiplicity on
active calls. For example, the decode case fits `2 * I_{units > 0} * Wait[...]`.
A synchronization that returns an error is still an observed attempted operation,
but does not establish successful completion. Already-satisfied synchronization
still counts; no claim about blocked duration is made.

```sh
bin/drperf-check-waits \
  /home/ubuntu/compression/ditto_kv/example/qwen2.5B/qwen.drperf.json \
  examples/waits/ditto_contracts.json \
  -o out/waits/ditto-declarations.json

python3 examples/waits/check_ditto.py \
  /home/ubuntu/compression/ditto_kv/example/qwen2.5B/qwen.drperf.json
```

The CLI exits 0 for observed verification, 1 for contradicted declarations, and
2 for incomplete/unverified checks (also used for invalid command input). The
Ditto example intentionally exits 2: the six declarations explain 43 CUDA
operations, while 16,573 mutex acquisitions and three semaphore operations
remain unexplained. Outside-region operations are disclosed separately; the
checker does not claim whole-program completeness.

`check_ditto.py` additionally tests deliberate mistakes and writes
`out/waits/ditto-contract-check.json`, including profile SHA-256, declarations,
per-claim results and exact counterexample invocation IDs / entry PCVs:

| D2H declaration | Observed result |
| --- | --- |
| `d2h == 1` | 9 present and 5 absent calls agree |
| declaration omitted | 9 unexplained stream dependencies |
| `True` | 5 predicted waits did not occur |
| `False` | 9 observed waits were omitted |
| `d2h == 0` | both errors: 9 unexpected presences and 5 unexpected absences |
| correct indicator, wrong producer | 9 producer mismatches |
| mutex indicator with an asserted owner | occurrence can agree; owner stays unverified |

**Observation limits:** the two `load.plan` declarations use `new_copy_stream`
as an observed proxy. The actual code tests `_ref_event is None` and
`last_codec_copy_end is not None`; those states are not PCVs in this capture.
Passing does not establish that the proxy remains valid in other executions.
The encode/decode declarations have only positive examples here; the output
explicitly reports that branch coverage. Empty `rt.wait` calls cannot verify a
producer attribution that was never exercised.

Indicators use entry PCVs, integer comparisons/arithmetic, `and`, `or`, and
`not`; no function calls, attribute access, or execution of supplied code.
The prototype accepts one declaration per region/API. It does not yet separate
multiple source sites with different guards/producers inside one such bucket.
Unsupported APIs (including currently unrecorded `cudaEventQuery`) are rejected,
not interpreted as zero observations. Incomplete traces/captures cannot verify
absence. The checker reconstructs producer links from event history rather
than trusting producer labels supplied with a declaration.

Tests: `python3 -m unittest discover -s tests -p test_wait_contracts.py`.

### Declared CPU/GPU event checkpoints and delayed-publication probes

The application can supply an event model directly, without requiring drperf to
infer high-level producer connections from native synchronization objects.
There is **no condition argument**. Put the markers inside the existing branch:

```python
# B, after preparing the result:
perfmark.event_publish(event_id, generation)
ready.set()  # original publication; must immediately follow the checkpoint

# A:
if original_condition:
    ready.wait()  # original code, not synchronization supplied by perfmark
    perfmark.event_waited(event_id, generation)
    use_result()
```

C has the equivalent `perfmark_event_publish` and
`perfmark_event_waited` functions in `perfmark.h`. IDs and generations are
unsigned 64-bit application identifiers, scoped to a captured process. They are
**not inferred pointer identities**. Use a fresh generation for each publication;
multiple consumers may share a generation, but multiple publications of one
generation are an annotation error. The marker API takes no indicator or PCV
expression. Observed waited counts can still be fitted against the enclosing
region's existing PCVs, including zero occurrences.

Start profiling before either side runs, and put checkpoints inside perfmark
regions. The checkpoints do not start late attachment on their own. In an
ordinary execution they do not implement synchronization. Only an explicitly
requested probe pauses a publishing thread. Python event checkpoints use a
GIL-releasing native call so the probe does not accidentally freeze the consumer.

The checker checks whether the matching publication checkpoint finished before
`waited` was entered. **No wait-begin checkpoint is needed.** Missing publications
remain unverified; wrong ordering and duplicate generations are violations.
Each checkpoint must belong to a captured region invocation. Region ownership
comes from that invocation, not a supplied display label. Missing invocations,
unfinished checkpoints, and record counts that disagree with capture metadata
cannot establish a checked relationship.
Timeout/cancellation paths must not emit `waited`. A published event without a
consumer makes no wait claim: without a begin checkpoint the checker cannot
identify a wait that never reaches readiness.

Native synchronization observations remain a separate coverage report under
`unexplained(Wait[?])`; without a begin boundary they are not assigned to the
nearest checkpoint. `status: ordered` describes the declared edges only, not
complete native synchronization coverage. An unannotated wait remains visible
through the existing native discovery mechanism where that API is supported.

Marker modules are excluded while counting, not by calibrated subtraction.
Python `event_publish` and `event_waited` are native builtins with explicit
exclusion boundaries: argument validation, GIL handoff and synchronous callees
are excluded as well. Internal synchronization in these helpers is not reported
as an application wait. Other threads continue to be counted. Caller-side
argument expressions and Python call dispatch remain application instructions;
this does not claim that inserting an annotation has zero total overhead.
Rebuild `_perfmark.so` with the client/library; a stale extension is rejected
when event annotations are used under drperf.

The event abstraction is shared by CPU and GPU code. **No new GPU interceptor is
required for the declared-event checker.** Place markers around the application's
existing publication and readiness boundaries. This prototype observes host
checkpoints: it does not infer actual GPU completion from kernel submission or
validate device stream ordering using CPU timestamps. A GPU completion claim
needs a checkpoint at a boundary where the application knows completion, not
merely where it enqueues work. Existing native synchronization discovery is
optional evidence for unknown-wait coverage, not the source of declared pairings.

The exporter adds `eventModel` to reports containing these checkpoints. Check or
plan a probe with:

```sh
bin/drperf-check-events baseline.drperf.json --plan
```

For each publisher, planning uses the largest observed publication-to-waited
wall-clock distance, adds 100 ms, and caps the proposed delay at 5 seconds. These
are diagnostic instrumented times, not performance predictions. Probe one
publisher region per rerun:

```sh
DRPERF_WAITS=1 DRPERF_WAIT_DELAY_KIND=event \
DRPERF_WAIT_DELAY_REGION=B DRPERF_WAIT_DELAY_MS=300 \
DRPERF_REPORT=out/probe.drperf.json bin/drperf python app.py
```

The delay happens **before the publication checkpoint finishes and before the
following original release executes**. It does not just falsify a timestamp
while allowing the real release through. Only declared publications in B are
delayed; native semaphore posts are not additionally delayed in `event` mode.
Keep probe profiles separate from baseline cost fits. A changed execution can
have different timing, so a delay planned from a baseline is an attempt to expose
a contradiction, not a guaranteed schedule inversion or a proof of necessity.

New captures retain the requested publisher region, delay kind, duration and
injection count. The checker compares that request with completed injected
records. A requested delay that never ran is reported explicitly and exits 2;
it cannot silently pass as a baseline run. Saved profiles undergo these checks
again when reloaded. Older profiles without the new request fields remain
readable, but cannot establish request details they did not record.

Native receive results distinguish data, zero bytes, and errors. A positive
byte count is successful; zero can mean EOF or an empty receive, depending on
the socket and request. Neither result identifies a remote publisher by itself.

Build and run the deliberately false examples:

```sh
./build.sh
python3 examples/waits/check_events.py
python3 -m unittest discover -s tests -p test_event_model.py
```

[events.c](examples/waits/events.c) includes correct, conditional, transitive,
missing-wait, wrong-pair, and omitted-annotation cases. Each baseline and probe
runs the real compiled program under DynamoRIO. Results and portable profiles
are written under `out/waits/events/`; [events.py](examples/waits/events.py)
provides the Python/GIL regression example.

| Example | Baseline | Delayed publication |
| --- | --- | --- |
| Correct semaphore wait | ordered | ordered; real wait holds the consumer |
| Conditional wait in original code | two present, two absent calls | ordered; occurrence formula is `need` |
| A waits B, B waits C | both edges ordered | delaying C propagates through B; both edges stay ordered |
| Missing actual wait | ordered by timing coincidence | consumer reaches waited before B publishes: violation |
| Waits on B but declares C | ordered by timing coincidence | delaying C exposes wrong declaration: violation |
| Real wait has no annotation | native semaphore dependency retained separately | no semantic declaration is invented |

The C probe runner derives its actual delay from each baseline; it does not
hardcode the expected event order into the checker. The Python test separately
checks that a 500 ms publication delay can expose a missing wait while preserving
a correct wait. This implementation has been exercised on CPU examples; it does
not claim a new GPU/GX execution validation.


### Ditto candidate-future experiment (publish + waited)

Run `python3 examples/waits/check_ditto_events.py`. It builds an annotated copy
of the actual `src/compressor/native/ditto_runtime.cpp`; the original Ditto tree,
installed libraries, and serving profiles are left intact. This is the real CPU
candidate algorithm, thread pool, cache and `shared_future.get()`, with no GPU
or fake candidate computation. Two workers process token lengths 8, 64, 256,
1024, then 8 again after eviction; each batch is fetched twice.

The worker publishes immediately before returning its result to the packaged
future. The consumer records `waited` after `future.get()` succeeds. IDs are
unique per new job; cache hits reuse the same publication and eviction/rebuild
allocates a fresh identity. In the deliberately false variant, only the `waited`
annotation moves before `future.get()`; the algorithm itself still waits.
A 200 ms driver pause makes that wrong annotation appear ordered in the baseline.
The runner measures the baseline gap and chooses the publication delay itself.

The initial run chose **301 ms** for each variant: the correct variant retained
all **10 ordered consumer checkpoints**, whereas the premature annotation
produced **5 violations** (one per newly built job). Cached rereads remained
ordered. Baseline and probe outputs in both variants matched the unmodified
library: checksum `6654681029067795999`. Delay size can vary between reruns.
The declaration-checking result does not explain every internal mutex/futex,
nor does this small subsystem test constitute a full Ditto serving run.

Review the exact inserted code in
[out/waits/ditto-events/annotations.patch](out/waits/ditto-events/annotations.patch),
the [annotated runtime](out/waits/ditto-events/ditto_runtime.cpp), and the
[results](out/waits/ditto-events/results.json). Portable profiles are beside them:
`correct-baseline.drperf.json`, `correct-probe.drperf.json`,
`premature-baseline.drperf.json`, and `premature-probe.drperf.json`.
The native exclusion regression deliberately adds a large loop inside a marker:
its instructions disappear even with wait discovery disabled, while the same
loop executed outside the marker remains counted.
