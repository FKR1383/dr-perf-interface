# LMCache case study: improving a KV-cache system with drperf interfaces

Goal: show that drperf's interfaces find and justify real improvements in a
system we did not write. Loop per improvement: read the interface, name the
term that dominates, predict how the interface changes under a fix, apply the
fix, recapture, compare predicted with measured. Each closed loop is one data
point for "drperf is useful".

Status 2026-09-29: baseline interfaces and fresh wait captures are available;
no LMCache optimization applied yet. The [wait-analysis study](docs/LMCache_WAITS.md)
checks remote future dependencies, tests event-loop blocking, and identifies
per-chunk barriers and implicit slot-mapping synchronizations. It includes an
interactive graph and exact source locations.

## Setup

Everything is in the ditto-kv repo (`/home/ubuntu/compression/ditto_kv`),
directory `example/qwen2.5B/lmcache/`:

| file | what |
|---|---|
| `lmcache_overlay/` | LMCache's own modules (upstream `8e93a34`) with perfmark regions written into them; commit `9f639e1` is pristine, so `git diff 9f639e1 -- example/qwen2.5B/lmcache/lmcache_overlay` shows every added line. Fixes go here too |
| `drperf_lmcache.sh` | the capture, inside the `gx-kimi-k3` container on icdslab2; `ARM=cpu`, `remote_naive`, `remote_cachegen` |
| `lmcache_cpu.drperf.json`, `lmcache_remote_naive.drperf.json` | baseline exports; open from the ditto-kv root so source links resolve |
| `interface_table.py`, `interface_tables.txt` | self, inclusive, fit and nested regions per region |
| `README.md` | how LMCache was made to run under GX, and the findings |

Workload: the tier capture's (`exp/gx_kimi/drperf_offline.py`, qwen preset):
Qwen2.5-0.5B, dummy weights, 40 MB GPU KV so every turn reloads from LMCache,
24 sessions x 6 turns, prompts 100-1,500 words = 1-8 LMCache chunks of 256
tokens (3 MB each). One request at a time, engine in-process.

Run (from the ditto-kv root; icdslab2 has the image, never `docker save` there):

```bash
rsync -a --exclude runs --exclude __pycache__ example/qwen2.5B/lmcache/ \
  icdslab2.epfl.ch:/home/ubuntu/ditto_kv_gx/example/qwen2.5B/lmcache/
ssh icdslab2.epfl.ch "bash ~/ditto_kv_gx/lmc_launch.sh remote_naive late NAME"
# wait for exit; check serve.log says DRPERF_SERVE rc=0 (the client can report
# 144/144 while the drperf report is invalid)
ssh icdslab2.epfl.ch "docker run --rm -v ~/ditto_kv_gx/runs/NAME:/r \
  --entrypoint /bin/chmod gx-kimi-k3:latest -R a+rX /r; docker rm NAME"
rsync -a --exclude lmcache_pkg icdslab2.epfl.ch:~/ditto_kv_gx/runs/NAME/ \
  example/qwen2.5B/lmcache/runs/NAME/
/home/ubuntu/drperf/bin/drperf-export example/qwen2.5B/lmcache/runs/NAME/raw \
  --source-root "$PWD" --max-trace 100000 -o OUT.drperf.json
python3 example/qwen2.5B/lmcache/interface_table.py OUT.drperf.json
```

`lmc_launch.sh ARM MODE NAME` (in the same directory, copied to the box) is
the DITTO_KV.md docker command with
`-e ARM=` and this script. `MODE=native` is a functional smoke run (3 min).
Both arms together take about 5 minutes late-attached.

## Region vocabulary

- `lmc.*`: LMCache functions and blocks (`lmc.store`, `lmc.retrieve`,
  `lmc.lookup`, `lmc.gpu.*`, `lmc.sm.*`, `lmc.local.*`, `lmc.remote.*`,
  `lmc.net.*`, `lmc.serde.*`, `lmc.vllm.*` for the vLLM connector entry points).
- `mv.*`: data-movement primitives, each with a `bytes` state, at every copy
  site: `mv.h2d`, `mv.d2h`, `mv.d2d`, `mv.h2h`, `mv.net.recv`, and `mv.sync`
  for a stream synchronisation. Redundant movement shows up as a multiplicity
  in the parent's composition, e.g. `lmc.store = 2.2 x mv.d2d + 2.2 x mv.d2h +
  2.2 x mv.sync`.

## Baseline interface (remote_naive arm, host instructions)

Per 256-token chunk, about 1.7M each way; the byte term is zero everywhere.

| region | calls | per call | note |
|---|---|---|---|
| `lmc.gpu.contiguous_view` | 469 | 1,169K constant | once per chunk, both directions |
| `lmc.gpu.to_gpu_chunk` self | 381 | 137K | load, per chunk |
| `lmc.gpu.from_gpu_chunk` self | 88 | 278K | store, per chunk |
| `mv.h2d` (3 MB) | 381 | 78K | chunk load launch |
| `mv.d2d` + `mv.d2h` (3 MB each) | 88 + 88 | 45K + 43K | store stages every chunk |
| `mv.sync` | 198 | 3K | one per stored chunk, one per retrieve |
| `lmc.local.alloc` | 469 | 81K | host buffer per received chunk |
| `lmc.net.exists`, `lmc.net.get_meta` | 421, 381 | 31K, 31K | blocking round trips per chunk |
| `mv.net.recv` (3 MB) | 381 | 58K | |
| `lmc.retrieve` self | 110 | 535K + 390 x tokens | 0.3% unexplained |
| `lmc.remote.get` | 110 | 32K + 37.5K x chunks | |

## Improvement tasks

Each: the fix, the predicted interface change, and how to check. Apply one at a
time in `lmcache_overlay/`, recapture both arms, and record the measured change
next to the prediction in the results table below. Keep the regions unchanged
so the before and after interfaces compare region by region.

### T1. Compute the KV layout once, not per chunk (largest term)

`gpu_connectors.py:138` `initialize_kvcaches_ptr` runs
`attempt_permute_to_contiguous_view` (`kv_format/contiguity.py:43`, not in
the overlay yet) over all 24 layers at the top of every per-chunk copy
(`:301` load, `:373` store). Its input, vLLM's KV tensors, is fixed after
start-up. Fix: cache the result keyed on the identity of the kvcaches list;
recompute only when it changes.

Predict: `lmc.gpu.contiguous_view` calls 469 -> 1 (or a few);
`lmc.gpu.to_gpu_chunk` inclusive 1,369K -> ~200K; `lmc.gpu.from_gpu_chunk`
inclusive 1,542K -> ~373K; `lmc.retrieve` inclusive drops 1.17M x chunks.

### T2. Real batching in `batched_to_gpu` / `batched_from_gpu`

`gpu_connectors.py:434-448` loop over chunks (upstream TODO "enable real
batching"); each chunk re-inits pointers (`lmc.gpu.init_pointers`) and
launches its own kernel. Fix: one pointer init and one launch over the
concatenated slot mapping per batch.

Predict: per-chunk self costs (137K load, 278K store) and `mv.h2d` launches
become per-batch terms; `lmc.gpu.to_gpu` fits `const + small x chunks`.

### T3. Store without the staging copy, one sync per batch

`gpu_connectors.py:406` pages -> `gpu_buffer` (`mv.d2d`), `:419` ->
pinned host (`mv.d2h`), `:428` `store_stream.synchronize()` per chunk.
Fix: gather straight into pinned host memory; synchronize once per batch.

Predict: `lmc.store` composition loses `2.2 x mv.d2d`; `mv.sync` per store
2.2 -> 1. Device bytes moved on store halve (visible as the `bytes` states;
the time saved is not visible to drperf, see Gaps).

### T4. One remote request per batch

`lm_connector.py:89` EXIST per chunk (via `remote_backend.py:164,190`), then
`:151` GET per chunk with a blocking metadata read and `:58` payload receive.
Fix: batched EXIST, and a batched GET that returns metadata and payloads in
one exchange.

Predict: `lmc.net.exists` 421 -> 134 (one per lookup); `lmc.net.get_meta`
381 -> 110 (one per retrieve); `lmc.remote.get` loses most of its 37.5K per
chunk.

### T5. Receive into a preallocated ring

`lm_connector.py:65` allocates from the local CPU allocator for every received
chunk (`lmc.local.alloc`, 81K, 469 calls) even with the local tier off.

Predict: `lmc.local.alloc` under `mv.net.recv` disappears; 81K x chunks off
`lmc.retrieve`.

### T6. Skip the local-tier put when the tier is off

`local_cpu_backend.py:192` is called on every store and write-back and
returns at `:206`. Small; a cleanup and a check that drperf sees a 1.8K term.

### T7. Fit quality before claiming numbers

`lmc.store` self is 25% unexplained by tokens and
`lmc.vllm.get_num_new_matched_tokens` 54%. Add a state for chunks already
stored (store) and chunks already known (lookup) and refit. Do this before T1
so the store-side predictions have a clean baseline.

## Results

| task | region | predicted | measured | capture |
|---|---|---|---|---|
| baseline | `lmc.gpu.to_gpu_chunk` incl | - | 1,369K | lmc-ovl4 |
| T1 | | | | |

## Gaps (what drperf cannot show here)

- **Waiting and stalls.** Fresh captures now count native synchronization calls
  and check declared future dependencies, including already-satisfied waits.
  They do not measure time actually blocked or critical-path latency; GX skips
  device computation in these runs. See the wait study for coverage limits.
- **Other threads.** `DRPERF_FOLLOW_THREADS=0` disables inherited regions on
  unmarked threads; it does not exclude explicitly marked event-loop regions.
  These are captured, including `lmc.net.exists`, `lmc.net.get_meta`, and the new
  completion checkpoints. Unmarked background work remains outside region costs.
  Inheriting regions across roughly 190 threads previously exhausted the 96 GB
  counter budget, so inheritance remains disabled.
- **CacheGen.** Under GX's functional skip, reductions return 0, so
  CacheGen's host logic breaks ("Max bins must be less than 64"). Its
  `to_bytes`/`from_bytes` are annotated (`storage_backend/serde/
  cachegen_basics.py:202,210`) but have not run. Needs a framework-test-style
  substitution like ditto's `DITTO_FRAMEWORK_TEST`, or a real-GPU run.

## Traps

- LMCache must be built from source (upstream `8e93a34`) for this vLLM build's
  KV layout; it lives in `~/ditto_kv_gx/pydeps_lmc` on icdslab2.
- A crashed engine leaves the container hanging: watch `server.log` for the
  first error instead of `docker wait`.
- `DRPERF_SERVE rc=2` with "region keys got no counter array" means an invalid
  report even though every request succeeded.
