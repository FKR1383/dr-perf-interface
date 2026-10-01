# Ditto wait-graph source audit

Audited 2026-09-29 against the actual captured source and raw synchronization records.

**Verdict: the five displayed region-pair links are supported as event-record dependencies. They are not a complete semantic wait graph, and they do not establish CPU stalls.** In particular, the nine store-drain synchronizations follow successful completion polling; the most useful completion gates in the serving/GC workflow are currently missing because event queries are not captured.

## Evidence and scope

- Profile: `/home/ubuntu/compression/ditto_kv/example/qwen2.5B/qwen.drperf.json`.
- Profile SHA-256: `18390b95365bafeaad80c0d84f82186426ab07923f382af2cfde07eb8bc31d7e`.
- Raw sidecar: `/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/raw/run.18.json.waits`.
- Source links below refer to the **captured snapshot**, not newer source files.
- All 106 exported source-location hashes match that snapshot. All 118,113 exported synchronization records match the raw sidecar on API, object, arguments, invocation, thread, order, and return status. No synchronization records were dropped.
- Independently checked every one of the 43 matched operations inside regions: successful wait/record, matching event handle and process, record completed before wait entry, and no intervening event record/create/destroy. Those 43 operations aggregate to five displayed region pairs: 33 queued stream dependencies and 10 host event synchronizations.
- The run used GX **functional emulation**, dummy weights, and `DITTO_FRAMEWORK_TEST=1`. It exercises production submission/control code with fake codec results. This audit does not validate real GPU execution, blocking durations, or all workload branches.

## Every displayed link

| Link | Observations | Source review and interpretation |
| --- | ---: | --- |
| `store.drain -> carrier.transfer` | 9 | [drain](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/store_engine.py:131) calls `inner.wait()`, whose [implementation](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/transport.py:41) synchronizes `end_event`. The transfer [records that event](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/transport.py:242) after copies and callbacks. Correct dependency on transfer-stream work. However, all nine captured drain invocations are under `worker.get_finished / worker.poll / rt.poll / rt.finish`. [Polling](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/runtime.py:708) checks `completion.done()` before calling finish, and [finish](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/store_engine.py:146) checks again before drain. Thus these synchronizations follow observed completion; the graph does not demonstrate nine CPU stalls. |
| `carrier.transfer -> carrier.transfer` | 9 | [D2H submission](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/transport.py:200) calls `stream.wait_stream(current_stream())`. All nine records and waits belong to the **same region invocation**, record on stream 0, and wait on the transfer stream; all have PCV `d2h=1`. This is D2H waiting for preceding compute-stream work, represented by an event recorded inside the transfer region. It is **not** evidence of nine transfer-to-transfer waits or CPU self-waiting. The separate `_last_end` serialization branch at line 205 is not what these nine matches show. |
| `codec.encode_units -> codec.encode_units` | 10 | [Annotated encode call](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/extent_encode.py:252) reaches [copy_stream.wait_event(torch_stream.record_event())](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/encode.py:148). Record/wait are in the same invocation, ordering the copy stream after encode work. Correct internal GPU stream dependency, not a CPU stall. |
| `codec.decode_units -> codec.decode_units` | 10 | [Annotated decode call](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/extent_decode.py:158) contains [copy-to-decode ordering](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/decode.py:186) and [joining decode lanes](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/decode.py:83); reference-copy ordering also exists at [line 283](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/decode.py:283). There are two matches in each of five decode invocations, all same-invocation event-record links. The region pair is supported. Records lack native/Python call sites, so the exact source statement for each individual API call is not independently proven by these records alone. |
| `load.plan -> load.plan` | 5 | This merges **two different meanings**: one same-invocation host synchronization in [_gpu_origin](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/load_engine.py:221) for a timing reference; four cross-invocation queued waits at [last_codec_copy_end](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/load_engine.py:450), whose event is [recorded near the end of load planning](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/load_engine.py:470). All four observed record/wait stream handles are equal, so these reinforce existing same-stream ordering rather than demonstrating extra cross-stream waiting. The single graph edge loses the API distinction. |

Raw record examples (IDs refer to `waits.events` / `waits.operations`):

| Region | Wait ID | Record ID |
| --- | --- | --- |
| `store.drain` | `0:18:143179` | `0:18:143013` |
| `carrier.transfer` | `0:18:142861` | `0:18:142831` |
| `codec.encode_units` | `0:18:147005` | `0:18:146975` |
| `codec.decode_units` | `0:18:202885` | `0:18:202855` |
| `load.plan` timing reference | `0:18:201565` | `0:18:201543` |
| `load.plan` prior-copy ordering | `0:18:212257` | `0:18:203377` |

The publisher region is where the event was **recorded**, not necessarily where all work covered by that event was submitted. The D2H/default-stream example makes that distinction material. Collapsing boxes preserves the correct enclosing invocation paths, but cannot recover that missing work provenance.

## Missing semantic dependencies

These are code-derived relationships, **not new measured edges**. Query return values and event generations at query sites were not recorded, so exact invocation matching and whether a poll actually postponed progress require another capture.

| Missing dependency / coverage | Exact source and evidence |
| --- | --- |
| Load/store completion polling: `rt.query` depends on transfer/codec completion. | [Runtime polling](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/runtime.py:686) invokes [codec_done()/done()](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/load_engine.py:95) and [transfer.done()](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/transport.py:38). A false query defers completion reporting. The run has 22 `rt.query` invocations, but **no query-derived edges**. Expected event publishers include `carrier.transfer` and `load.plan`; query identity/results are absent, so do not assign measured counts. |
| Encode metadata readiness: `codec.blob_sizes` depends on `codec.encode_units`. | [Size polling](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/extent_encode.py:323) reaches [DeferredEncode.ready()](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/encode.py:49), which queries events [recorded after encoding/header copies](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/encode.py:193). `None` postpones output submission. Ten size-poll regions were observed, but this gate is absent from the graph. |
| GC publication: `gc.publish` depends on `codec.submit_output`. | [Publication](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/compaction.py:958) returns to later polls until `batch.event.query()` succeeds at line 983; the completion event comes from [deferred D2H output](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/encode.py:342), called inside [codec.submit_output](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/extent_encode.py:336). The capture has 74 publication and ten output-submission regions. Fake output preserves this fence through [_FakeOutputEvent.query](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/framework_test.py:738). A particularly important missing dependency for explaining the compression workflow. |
| PCV probes also query completion. | [_pcv_publish](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/compaction.py:360) calls `batch.event.query()` while computing PCVs, before the actual publication region. A future query collector must distinguish annotation/probe work from application polling rather than introducing misleading probe-region dependencies. |
| Workspace recycling and exhaustion. | Rust [reap](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/ftl-core/src/lib.rs:1143) queries pending fences; [lease exhaustion](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/ftl-core/src/lib.rs:1318) synchronizes a pending event before retrying allocation. Query-based recycling is invisible. This profile contains no codec host event synchronizations, so the exhaustion fallback is not established as exercised. Error cleanup also synchronizes streams at [lease release](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/ftl-core/src/lib.rs:1518). |
| Native CPU candidate readiness. | [Candidate building](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/encode.py:861) submits work then retrieves results. The native [shared_future.get()](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/native/ditto_runtime.cpp:469) depends on [pool jobs](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/compressor/native/ditto_runtime.cpp:217). drperf has no future-to-job provenance mapping. Even observing a libc lock/condition or futex would not identify the producing job. This audit does not claim that any particular get blocked in this run. |
| Handle-lock/resource waits. | Native [read locking](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/ftl-core/src/handle_manager.rs:2125) and [write locking](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/ftl-core/src/handle_manager.rs:1830) wait for resource predicates; [unlock](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/ftl-core/src/handle_manager.rs:616) notifies waiters. Mutex owners and condition predicates are not resolved by the current checker. Captured lock calls do not prove contention. |
| Conditional conflicts, shutdown, aborts, and alternate codec configurations. | [Conflicting stores](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/store_engine.py:187) may drain earlier transfers; [explicit job waits](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/runtime.py:766) may wait for outstanding jobs; [load abort](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/load_engine.py:137) and [GC abort](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/compaction.py:920) drain streams. The ten observed `rt.wait` calls all have `jobs=0`; no captured drain occurs under `store.wait_conflicts`. These branches cannot be declared covered just because the regions appear. CPU codec, workspace pressure, serial decode, contention and error paths need separate workloads. |

A useful semantic sketch, with **missing** edges explicitly marked, is:

```text
rt.query          --[missing completion query]--> carrier.transfer / load.plan
codec.blob_sizes  --[missing completion query]--> codec.encode_units
gc.publish        --[missing completion query]--> codec.submit_output
store.drain       --[captured event sync]-------> carrier.transfer
```

Do not add an inference-to-GC wait merely because GC is pending: [source-lease flushing](/home/ubuntu/compression/ditto_kv/exp/gx_kimi/runs/drperf-graph-qwen-20260928/source/src/cache/compaction.py:800) deliberately marks in-flight compactions aborted and postpones their cleanup instead of waiting for them.

## Why no dropped records is not completeness

The hook list in [client/waits.h](/home/ubuntu/drperf/client/waits.h:18) omits `cudaEventQuery` / `cudaStreamQuery`, future provenance, CUDA driver equivalents, and arbitrary application predicates. [lib/waits.py](/home/ubuntu/drperf/lib/waits.py:23) resolves a narrow set of event/semaphore/stream mappings; it deliberately leaves mutex/condition ownership unresolved.

The profile contains 16,619 recognized operations inside regions: 43 matched operations, **16,573 unresolved mutex acquisitions and three unresolved semaphore waits**. Outside regions, another 291 matched event operations have no named region endpoints, and millions of libc housekeeping operations are only aggregated. These are coverage facts, not estimates of time blocked or a percentage of semantic waits discovered. The UI's **All waits (5)** currently means all *matched region-pair links*, not all waits in Ditto.

## Current source versus captured source

The current `src/cache/transport.py`, `store_engine.py`, `load_engine.py`, `src/compressor/encode.py`, `decode.py`, and `framework_test.py` match the snapshot byte-for-byte. Current `runtime.py` and `compaction.py` add compression-admission controls (`allow_compression` / `allow_launch`); the polling gates above remain. Current `ftl-core/src/lib.rs` adds a standalone module declaration; the audited workspace wait logic is unchanged. The profile should not be presented as coverage of newly added configurations.

## Next changes justified by this audit

1. Capture event-query results with object generations, and show **completion checked / pending / satisfied** separately from blocking synchronization and queued stream dependencies. A query alone does not prove that the application deferred work; link the API observation first and retain that limitation.
2. Keep event publisher attribution separate from the region that submitted the required GPU work. Recovering the latter needs stream submission history (including kernels and imported stream dependencies), not just the event-record site.
3. Split the `load.plan` edge by API/dependency kind and show unresolved-operation coverage alongside matched arrows. Preserve same-invocation/internal versus prior-invocation evidence.
4. For completeness beyond this workload, exercise workspace pressure, conflicting stores, outstanding-job waits, native futures/locks and cleanup paths. Never manufacture dependencies merely from temporal proximity or an injected delay.

This audit did not change Ditto, add wait annotations, invent missing profile edges, or claim native GPU timing validation.
