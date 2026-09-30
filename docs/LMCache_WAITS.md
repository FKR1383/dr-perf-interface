# LMCache: instruction counts plus checked waits

This is a record of local experiments. Links into `out/waits/lmcache/` refer to
local captures and source overlays, which are not included in the Git repository.
The portable marker examples and checker tests are in `examples/waits/` and
`tests/`; the commands below that use LMCache also need those local artifacts.

2026-09-29. This extends the [LMCache instruction-count study](../lm_cache_task.md)
with native synchronization observations and passive future-completion checks.
The existing LMCache code and old profiles were left unchanged; checkpoint
annotations live in a separate [overlay](../out/waits/lmcache/overlay/).

## Semantic regions, rather than synchronization helpers

The current annotations place `waited` in the **caller that consumes the result**.
For example, `lmc.remote.get` waits for a connector GET operation; an implementation
helper such as `Future.result()` does not own the semantic dependency. Marking that
helper separately for instruction accounting must not change the declared edge.
See [waited.md](waited.md) for the API and checking contract.

The connector's original coroutine executes inside an operation region:
`lmc.remote.exists_operation`, `lmc.remote.get_operation`, or
`lmc.remote.put_operation`. These contain actual connector work, rather than a
marker-only `*_ready` region. The [annotation adapter](../out/waits/lmcache/overlay/lmcache/_drperf.py)
closes the region when the coroutine suspends and reopens it when it resumes, so
interleaved tasks cannot become its children. Publication occurs inside the final
step, before the original Task/Future is released. A region invocation therefore
means an active coroutine step, not necessarily one whole asynchronous request.
The [adapter check](../out/waits/lmcache/check_operation_steps.py) exercises
interleaving, exceptional completion, and cancellation.

The consumers are lookup (`lmc.remote.contains`), retrieval (`lmc.remote.get`),
and store completion bookkeeping (`lmc.remote.put_callback`). The last is an
already-ready future consumed by a callback, not evidence of a sleeping thread.
For this connector, PUT completion means its send coroutine returned; it does
**not** establish remote durable storage or acknowledgment.

The fresh baseline completed 144/144 requests with no failures. All **890**
declared dependencies were ordered, with zero violations, zero unverified pairs,
and no instruction-count or trace validity errors:

| Consumer region | Publisher region | Checked occurrences |
|---|---|---:|
| `lmc.remote.contains` | `lmc.remote.exists_operation` | 421 |
| `lmc.remote.get` | `lmc.remote.get_operation` | 381 |
| `lmc.remote.put_callback` | `lmc.remote.put_operation` | 88 |

This adds **one new semantic relationship**, the store-completion callback, and
relocates the two existing lookup/retrieval declarations from primitive or
marker-only regions to application operations. For every observed retrieval
invocation, the number of GET dependencies equals its `chunks` PCV. Each lookup
and store callback has one dependency. The current graph has 38 region names and
four distinct wait relationships: these three declarations plus the previously
captured native `mv.sync → mv.d2h` relationship.

- [Current standalone graph](../out/waits/lmcache/lmcache-waits.html)
- [Current baseline evidence](../out/waits/lmcache/operations-analysis.json)
- [Current viewer report](../out/waits/lmcache/operations.drperf.json)
- [Current raw captures and annotation sources](../out/waits/lmcache/operations-evidence.tar.gz)

The viewer report is now **4.7 MB**. Earlier exports embedded the full native
synchronization history plus duplicated operation records, producing a 566 MB
JSON. The exporter now stores full evidence in a checksummed adjacent sidecar
(13.9 MB here). All costs, breakdowns, traces, and checked graph results remain
in the JSON; reloading the evidence reproduces all 890 checks exactly.

The new [publication-delay rerun](../out/waits/lmcache/operations-probe-analysis.json)
also completed 144/144 requests. It injected **117 ms at all 88 PUT publications**;
all 890 declared dependencies remained ordered, with no violations, unverified
pairs, dropped wait records, or count/trace validity errors. Both runs retain four
unfinished background native waits separately. This checks observed publication
order under the perturbation; it does not establish time blocked or all-schedules
correctness. The complete delayed profile is
[available as JSON](../out/waits/lmcache/operations-probe.drperf.json).

Native socket/lock observations remain separate. No annotation claims that a
client operation is the remote server's producer, or that host-side GPU submission
means device completion. This capture uses the synchronous retrieval configuration;
it does not exercise LMCache's separate asynchronous prefetch path.

## Workload and earlier evidence

Qwen2.5-0.5B-Instruct, dummy weights, one request at a time, 24 sessions × 6 turns,
40 MB device KV budget, 256-token chunks, and the `remote_naive` LMCache backend.
The installed LMCache package is pinned to `8e93a34`; the annotated source is the
existing `example/qwen2.5B/lmcache/lmcache_overlay` checkout. The remote cache server
runs in the same container. This is the specific `lm://` connector and synchronous
retrieval path, not a claim about every LMCache backend or configuration.

The real framework runs under **GX functional emulation and drperf**, without a
GPU or GXVM timing. Counts describe observed host instructions and synchronization
operations. They do not measure GPU latency, time actually blocked, or a critical
path. Results from the delay probe must not be used as baseline performance data.

- [Instruction/native-wait baseline evidence](../out/waits/lmcache/baseline-analysis.json)
- [Checkpoint-annotated evidence](../out/waits/lmcache/futures-analysis.json)
- [Complete checkpoint profile, compressed](../out/waits/lmcache/futures.drperf.json.gz)
- [Raw evidence archive](../out/waits/lmcache/evidence.tar.gz), including the original
  baseline, checkpoint run and delay probe with their process logs and sidecars.
- [Interactive region graph](../out/waits/lmcache/lmcache-waits.html): updated to the
  current capture above, with expandable hierarchy and cost details.
  The HTML retains graph evidence and summaries; omitted low-level native records
  remain in the raw captures. It is a visualization snapshot, not a fresh checker input.
- [Exact checkpoint patch](../out/waits/lmcache/annotations.patch)
- [Publication-delay plan](../out/waits/lmcache/probe-plan.json)
- [Completed delay-probe evidence](../out/waits/lmcache/probe-analysis.json)
- [Event-loop check source](../out/waits/lmcache/check_event_loop.py) and
  [three-trial output](../out/waits/lmcache/event-loop-check.log)

Both unperturbed runs completed 144/144 requests, exited with `DRPERF_SERVE rc=0`,
and have complete region traces, zero dropped wait records, and no count/trace
validity errors. Four background semaphore waits were still open at process exit;
they remain explicitly unresolved.

The delay run also completed 144/144 requests and exited successfully. It injected
117 ms before each of 381 GET publications. All 802 declared relationships remained
ordered, with zero violations or unverified relationships and no dropped records.

## Observed interfaces

These are **counts of dependencies or synchronization calls**, not durations to
add to a latency formula. `chunks` is the existing region-entry PCV. The relations
below hold for each observed invocation, not just an average across invocations.

| Region | Observed interface | Workload total |
|---|---|---:|
| `lmc.remote.contains` | `1 * Wait[exists_ready]` | 421 dependencies |
| `lmc.remote.get` | `chunks * Wait[get_ready]` | 381 dependencies in 110 batches |
| `lmc.gpu.from_gpu` | `chunks * cudaStreamSynchronize` | 88 syncs in 40 batches |
| `lmc.gpu.to_gpu` | `1 * cudaStreamSynchronize` | 110 syncs in 110 batches |
| slot-mapping uploads inside `mv.h2d` | sync hidden inside a tensor copy | 150 syncs: 110 load, 40 save |

There were 134 lookup-region invocations and 421 remote EXISTS exchanges. GET
also performs one metadata receive per chunk, followed by payload receives.
Payload `recv` counts vary with socket fragmentation, despite equal 3 MB payloads:
1,190 calls in the native-wait baseline and 1,485 in the checkpoint run. A single
coefficient on bytes does not explain that receive-loop work exactly.

The native semaphore waits are not equivalent to semantic dependencies: only
149 `sem_clockwait` calls occurred inside the 381 GET result checks in the annotated
run. Some futures were ready before their result was consumed. The checkpoints
retain all 381 relationships, including already-satisfied ones.

## Design choices worth improving

### 1. The asynchronous connector blocks its event loop

[`exists`](../out/waits/lmcache/overlay/lmcache/v1/storage_backend/connector/lm_connector.py:85)
uses synchronous `sendall` and `recv` inside an `async def` and a shared socket lock.
[`get`](../out/waits/lmcache/overlay/lmcache/v1/storage_backend/connector/lm_connector.py:143)
also reads metadata synchronously, then calls the synchronous payload receive loop.
Submitting multiple GET futures does not make those network transactions concurrent.

This is more than a naming concern. The component test calls the **actual EXISTS
method** over a socket pair and withholds its response for 200 ms. An unrelated
callback queued on the same event loop cannot run until the response is released.
All three trials reproduced that behavior. This test establishes the scheduling
effect; it does not quantify production contention or end-to-end slowdown.

**Candidate change:** nonblocking socket operations with complete-message reads,
plus explicit scheduling/backpressure. Preserve a lock around a complete protocol
transaction; merely making `recv` awaitable does not safely multiplex this protocol.
Consider separate bounded load/store queues or connections if measurements show
that large transfers delay other operations. The existing GET comment intentionally
favors loading over saving; replace that implicit policy with an explicit one.

### 2. Chunk-by-chunk remote metadata gates the caller

[`contains`](../out/waits/lmcache/overlay/lmcache/v1/storage_backend/remote_backend.py:164)
submits EXISTS and immediately calls `future.result()`.
[`batched_contains`](../out/waits/lmcache/overlay/lmcache/v1/storage_backend/remote_backend.py:188)
falls back to individual lookups for this connector. The graph checks 421 caller
dependencies on the corresponding EXISTS completion checkpoints.

**Candidate change:** implement a real prefix/batched EXISTS operation, preserving
first-missing-chunk semantics. This can replace per-chunk round trips with one batch
round trip. Similarly, the GET fallback
[submits individual futures](../out/waits/lmcache/overlay/lmcache/v1/storage_backend/remote_backend.py:453);
batching the wire protocol could reduce its 381 metadata exchanges toward one per
retrieval batch. An API called `batched_get` is insufficient by itself.

The existing `tokens` PCV does not encode remote residency. Prefix hits, misses,
and in-flight puts can change how many keys must be checked. Treat these as missing
state or unexplained behavior rather than claiming a universal formula in tokens.

### 3. Stores synchronize every chunk instead of every batch

[`from_gpu`](../out/waits/lmcache/overlay/lmcache/v1/gpu_connector/gpu_connectors.py:424)
synchronizes after each host-bound copy. Its
[batch wrapper](../out/waits/lmcache/overlay/lmcache/v1/gpu_connector/gpu_connectors.py:445)
calls it repeatedly. The measured multiplicity is exactly `chunks`. The load-side
batch wrapper already synchronizes once after its loop.

**Candidate change:** enqueue each batch's ordered gather/copy operations on the
store stream, then synchronize once before handing host buffers to storage.
For this workload the proposed change is **88 → 40 explicit store syncs**. That is
a structural prediction, not a measured optimization or a latency speedup. Keep
host buffers alive, preserve shared staging-buffer reuse on the same stream, and
retain the standalone `from_gpu` completion contract. Do not just delete the sync.

Native CUDA observations matched 88 `mv.sync` calls to preceding `mv.d2h` transfers.
The 110 load syncs remain unresolved at producer level: the transfer kernel is not
represented by the selected memcpy hooks. No false `mv.h2d` producer was invented.

### 4. Tiny metadata uploads also impose host synchronization

The vLLM adapter's slot-mapping
[load copy](../out/waits/lmcache/overlay/lmcache/integration/vllm/vllm_v1_adapter.py:813)
and [save copy](../out/waits/lmcache/overlay/lmcache/integration/vllm/vllm_v1_adapter.py:1172)
use `.to(self.device)` without `non_blocking=True`. Native interception finds 150
stream synchronizations inside these copies, separate from the 198 explicit
`mv.sync` calls. This is additional overhead that a search for explicit sync calls
would miss.

**Candidate change:** reuse appropriately pinned host/device metadata buffers and
enqueue copies with explicit stream ordering before dependent kernels. Validate
buffer lifetime, reuse and cross-stream dependencies; changing the flag alone is
not the complete design. At the outer adapter regions, `reqs` alone does not explain
the sync counts: only requests whose load/save conditions pass take these paths.

## How the dependency check works

The [separate annotation wrapper](../out/waits/lmcache/overlay/lmcache/_drperf.py:39)
assigns each submitted future a unique event generation. It publishes immediately
before its coroutine returns, and records `waited` immediately after the original
`future.result()` succeeds. It adds no readiness condition and does not replace
the original wait. Regions do not span an `await`, because coroutines can interleave
on one execution thread. Marker implementation instructions are excluded by drperf;
these added Python wrappers still change some caller overhead, so use the original
baseline for instruction-count priorities.

All 802 declared dependencies in the unperturbed checkpoint run are ordered, with
no missing publisher or order violation. The automatically chosen GET publication
delay is 117 ms: the largest observed publication-to-consumption gap, 16,868 us,
rounded up to milliseconds, plus a 100 ms margin. The probe delays publication
before the original future release. The marker binding releases the Python GIL
during the delay. This is an observed-order check under perturbation, not a proof
of dependency necessity for every input or schedule.

Raw socket receives still have unknown remote producers, and native synchronization
is not silently assigned to the nearest declared checkpoint. The graph is deliberately
conservative. In particular, it does not claim that every lock call was contended.

## What this adds to the instruction-count view

The instruction baseline still points to repeated
[KV layout normalization](../out/waits/lmcache/overlay/lmcache/v1/gpu_connector/gpu_connectors.py:138):
469 calls at about 1,169,000 host instructions each, approximately 51% of the captured
LMCache-region instructions in this workload. Cache that result while the relevant
tensor identities/layouts remain unchanged. This is a CPU-work candidate.

Wait analysis adds a different set of questions: why must the caller wait per chunk,
why does one slow socket prevent unrelated loop work, and which ordinary operations
implicitly synchronize? The next useful evaluations are nonblocking connector I/O,
batched metadata requests, and one store barrier per batch. These proposals have
not yet been implemented or validated as end-to-end speedups on a real GPU.

## Capture and reproduction

The [launcher](../out/waits/lmcache/launch.sh) uses the existing remote development
image and mounted workspace on `icdslab2.epfl.ch`, with `DRPERF_WAITS=1`, one million
wait-record slots, and GX excluded from instruction counts. An isolated copy of
drperf is mounted at `/home/ubuntu/drperf` in the container. The
[driver](../out/waits/lmcache/drperf_lmcache.sh) accepts `LMC_OVERLAY`; warmup and
settling invocations are not application-region measurements. Synchronization
capture attaches before engine construction to retain object histories.

```
# Remote host; existing image, package, model config and GX mounts required.
bash ~/ditto_kv_gx/lmc-waits/launch.sh remote_naive lmc-waits-baseline-NEW
LMC_OVERLAY=/w/lmc-waits/overlay \
  bash ~/ditto_kv_gx/lmc-waits/launch.sh remote_naive lmc-waits-futures-NEW
LMC_OVERLAY=/w/lmc-waits/overlay \
DRPERF_WAIT_DELAY_REGION=lmc.remote.put_operation DRPERF_WAIT_DELAY_MS=117 \
  bash ~/ditto_kv_gx/lmc-waits/launch.sh remote_naive lmc-waits-probe-NEW
```

The current captures are `lmc-waits-20260930-operations` and
`lmc-waits-20260930-operations-probe`. Earlier
capture directories are `lmc-waits-20260929-remote-ext`,
`lmc-waits-20260929-futures`, and `lmc-waits-20260929-probe-get` under the remote
workspace's `runs/`. The analysis scripts and local evidence are together in
`/home/ubuntu/drperf/out/waits/lmcache/`. Use the complete raw captures to re-export
or recheck; the HTML is only a compact display snapshot.

To recover the current raw folders and sources, extract `operations-evidence.tar.gz`
in `out/waits/lmcache/`; `evidence.tar.gz` holds the earlier experiments. Open `operations.drperf.json` directly in VS Code. The adjacent
`operations.drperf.json.waits.<hash>.jsonl.gz` contains full evidence for rechecking;
the viewer does not load it. `futures.drperf.json.gz` is the earlier capture. The much smaller standalone HTML opens directly in
a browser. Full native records are large because synchronization capture also
retains object histories and interpreter/allocator lock calls; those counts are
not evidence that the locks were contended.

During this study the exporter was fixed to retain unfinished background waits
without invalidating unrelated completed dependencies. Mappings for every affected
object remain disabled; unfinished application-region calls and dropped records
still invalidate the applicable capture. Wait and event checker tests cover this.
Validation passed: 24 wait tests, 17 event-checker tests, and 12 execution-graph tests.
The standalone HTML was also opened in Chromium: 38 distinct regions represented
by 45 hierarchy boxes, three wait edges, and no JavaScript errors.
