# drperf cases on the ditto-kv FTL

Each case below is a measurement on the Rust FTL core of ditto-kv (branch
`perf/ftl-annotations`, clone at `vllm-ditto/`), run under drperf on CPU, that
changed what one would do next. The measurements are instruction counts per
call, exact and reproducible for these single-threaded drivers, expressed as a
function of the states each region declares, with each coefficient attributed
to the functions that produced it, and with the relations between regions that
held exactly at every trigger of the run.

The team's own list of remaining fixes (`vllm-ditto/docs/ftl_overhead_potential_fixes.md`,
"Potential fixes (not done)") is the yardstick: three of its items are sized
here, and the ranking drperf gives them is not the one the list implies.

Production sizing used throughout, from the code and that document: 32 io-blocks
per superblock (`ditto_block_tokens` 8192 / `ftl_io_tokens` 256, the defaults in
`src/integration/vllm/spec.py`); the documented run of 40 sessions x 24,576
tokens is 96 io-blocks per session, so about 120 resident superblocks with one
KV group, and the document itself says "a few hundred"; a full-context reload is
a `plan_load` of 96 requests; a completed-superblock store is a bind of 32.

## The cases as slides: fit, surprise, optimise

Each case is meant to be told in three beats. First the fit: declare states,
drive them, and bring the unexplained share down until the formula is a
cost model. Then the surprise: a coefficient, attributed to a function, that
says the code is paying for something it should not. Then the optimisation,
with the same run before and after. "Measured" below means the third beat
was run in an experiment copy or branch and the coefficient moved as
predicted; "predicted" means only the first two beats exist.

| case | fit | surprise | optimise |
|---|---|---|---|
| FTL 2, lookup clones | `lookup = 44.9*fill - 221`, 0% irregular; callers at 4x, 4x, 1x of it | 45 instructions per resident io-block per lookup, for a key or two booleans; three call sites | measured: every `fill` coefficient exactly 0 after a no-clone `locate()`, identical results |
| FTL 3, bind_batch old vs new | old `1,899*req + 330*blocks + 947*superblocks`; new needs an exact-size driver to reach 19.5% | the old core scales with the whole directory; the new one still spends ~44% of a bind on string-keyed B-tree search | measured: hash-keyed map, 377k to 304k per bind, the size dependence gone |
| FTL 6, `_ordered_blocks` | `2,050*n + 417*n^2 + 4,943`, 16% | the `blocks` getter clones the map per offset: a quadratic for a tuple | predicted from the one-getter region: `n^2` coefficient 0, 497k to 54k per call at 32 |
| FTL 7, `ensure_row` | `35.1*full_slabs + 381*new_slab + 2,397` | every row walks every exhausted slab; grows with pool fill | predicted: keep non-full slabs only, coefficient 0 |
| FTL 8, `_clear_digests` | `288.4*digests + 7,395`, 0% | the whole digest table copied per retired block, ~35M per retired superblock | predicted: key-to-identities index |
| FTL 1, admission scan | `23.3*superblocks + 3,331`, 2%, plus the relation `superblocks = count(commits) - cum(frees)` | no surprise: 6k per step; the listed fix is not worth making | not needed |
| FTL 4, `count()` | `1,897*entries + 1,060` | the whole stats dict round-trips per bump, ~58k per call | predicted: counters in Rust |
| vLLM A, scheduler side | `prepare_inputs = 758*reqs + 107*tokens + 464,928`; `cached_request_data = 4,907*running + 13,108`, 4% | a 580k fixed tax per step against 758 per request; a per-step rebuild of unchanged state | measured: constant 465k to 205k (-56%), `copy_to_gpu` was copying tensors onto themselves on this backend; rebuild 4,916 to 1,671 per running request (-63% at 64) |
| vLLM B, admission | `process_inputs = 315.6*tokens + 372,903`, 4% | the per-token slope is `max`/`min` over the ids; 373k fixed per request is a `deepcopy`; the tokenizer is not cached; `Request.__init__` has a 128-token staircase | measured: 315.6 to 109.2 per token (`process_inputs`), 544.8 to 227.5 (`engine_add_request`); staircase re-declared to 43,273 per block, hashes made lazy: 692k per 2k prompt moved off admission, not removed |
| vLLM C, input batch churn | `add_request = 275*prompt_tokens + 46k`, 3%; `condense = 12,163*empty + ...` | admission converts the prompt element by element; a departure costs per row moved, not per token | measured: 275 to 203 per token after testing ten candidates (most worse than status quo), metadata rebuild -46%, condense -28% per row only in bursts |
| vLLM D, penalties | `pen_tensors = 310*total_tokens + ...`, 5%; relation `max_len = step index` | every step re-encodes every token generated so far: a quadratic | measured: 309.9 to 3.0 per token, outputs byte-identical, ~10 G saved at 64 x 1,000 |
| vLLM E, output path | first read `82,643*num_outputs + 12,843*num_active` with 7 nested markers; 2 markers: `30,154*num_outputs + 13,664*num_active`; marker-free 8,248 per request per step | the surprise was the markers: ~11k construction each, five per request per step; the objects were never built per step | measured: skipping the early-return call, 8,248 to 6,989 (-15%); lazy text join measured and rejected, as the formula predicted |
| Wan 2.1 (diffusers), host side | `rope = 29.9*frames + 312,303`; `cond_embed = 3,855*batch + 617,350`; `sched_step` 0.1% | rotary table rebuilt on every forward though it depends only on shape; prompt re-projected every step and CFG branch; VAE per-frame cat | measured: rope 482,987 -> 58,612 per call (-88%), cond_embed -28%, cat 10x at production width; latents and video byte-identical |
| Wan B, rotary apply, callbacks, posterior, tiling | `attn_rope = 5,764*seq_len + 320,506`, 0.4%; `dgd_init = 14.2*numel + 114,569`, 2.7%; `callback_step = 14,020*ninputs + 10,873` | rotary application is 45 instructions per element of pure iterator overhead; `locals()` per callback name; `exp` over the latent for a value never read; blend loops 114k per row | measured: posterior 40x, callback 33x, rotary -1.5% instructions but -25% wall; blend loops left alone because the formula says the vectorised form loses |
| vLLM G, scheduler under pressure | `sched_preempt = 2,140.5*running + 94,086`, 14.9%; `schedule` waiting coefficient exactly 0 under `max_num_seqs` saturation | the earlier 55k-60k "per waiting request" was aliasing; the real costs are a ~200k re-evaluation of the head request every step while KV is full, and five linear scans of `running` per preemption | measured: head memo removes 109 of 132 wasted evaluations (-56.5% on the region), preemption slope 2,140.5 -> 422.8 per running request; admission order, victims and peek counts byte-identical |
| Wan C, per-step constant decomposed | 55 probes split `denoise_step`'s 12M constant into sub-steps; `ax_qkv` 378,712 per layer with `sgemm` 130k in a constant | cross-attention re-projects the fixed prompt in every block of every forward, 3,000x per video instead of 60x; timestep, modulation, fp32 upcast, `Dropout(p=0)` all redone per branch | measured: `ax_qkv` -64%, host tax -9.8% per video, 14.2 TFLOP per video of GPU work removed; latents identical |
| vLLM H, n-gram speculation | `ngram_scan = 9,822*num_valid + 22.9*ctx + 33,258`, max residual 1.1%; `execute_model` per scored token flat at 176-182M | the KMP scan walks the whole context every step though only the last `max_ngram` tokens matter; rejection sampling costs 61% more per token than sampling while the forward gives back 3.2% at most | measured: K=3 and K=5 are a wash (70.5 / 73.2 / 73.2 tok/s), as the two coefficients predicted; the scan replaced by a first-occurrence index, 22.9 to 0.9 per context token, 2.13M to 0.88M per step at 64 x 1,000, drafts byte-identical, break-even after 16 steps |
| vLLM H2, stop strings and logprobs | `check_stop` 4,196.8 flat, 0.0%; `gather_logprobs = 1,009,495*num_reqs + 115,043` | stop strings are free (the suspected quadratic is not there); one request's `logprobs=5` bills every row of the batch | measured: top-k only on asking rows, other-thread part -29.1%, outputs byte-identical, wall unmoved at 8 threads |
| Wan D, text encoder padding | `t5_enc = -1.2*rtok + 24,402*ptok + 20,723*sq + ...`; with `lsq` 17.7% | the prompt is free and the padding is paid quadratically; 16x the encoder work at production, and an L² position bias rebuilt per layer | measured: encode at the real length, 47.7x per call at 8 tokens, bit-identical in fp32 on CPU but only numerically equivalent in bf16 on GPU (different reduction order); shortening the cross-attention keys rejected, the model attends to its padding |
| **Gradio (third party), streaming chat** *(measured, not fixed)* | every streamed chunk re-postprocesses, re-serialises and re-validates the whole conversation, then diffs it to find that only the last message changed | `per_message = 31,611.7*n`, `diff = 1,258*n`, `check_format = 939*n`, all at 0-3.5% irregular; ~49,500 instructions per message per chunk | per-chunk wall time 0.015ms to 1.268ms as the chat reaches 160 messages (85x); a 500-token reply then spends 0.63s in postprocessing, about 25% overhead against a 200 tok/s stream |
| **ComfyUI (third party), workflow cache keys** | the cache that makes re-runs cheap computes its keys from every node's full ancestor set, on every prompt, before any work; deep workflows are quadratic, wide ones linear | affine fit in `n` alone leaves 74.4% irregular; declaring the squared state gives `cost = 56,152.8*n + 318.1*n_sq - 563,031` at 6.1%, with 80% of the per-depth cost in `to_hashable` | measured: signatures built bottom-up, memoised and shared by reference; 800-node chain **8,312ms to 4.42ms (1,881x)**, diamond 2,274x, per-node cost flat at 5.5us; `n_sq` coefficient 318.1 to 0.351; equality partition identical on 62 workflows, invalidation identical on 1,409 checks, 67 upstream tests pass |
| **FramePack (third party), causal video generation** | the section loop is constant-cost by design, but `save_bcthw_as_mp4(history_pixels, ...)` inside it re-encodes the whole accumulated video every section, so an S-section run encodes S(S+1)/2 sections' worth of frames | drperf prices one section's save as `cost = 280,726,953*section + 204,804,779` instructions, attributed across the Python boundary to `x264_8_trellis_coefn` and the NumPy conversion feeding it; the fixed writer's per-section coefficient is 39,147, a factor of 7,170 lower | measured: each frame encoded once, written frames dropped from memory; **generation rate stops decaying** — stock falls 0.8867 to 0.5816 fps across a 30s video (34% lost) while fixed holds ~0.90 fps flat; **1.28x end to end on an A100** (1,276.9s to 994.8s, 282s saved, 1.57x projected at 60s and 2.15x at 120s), 25 output files to 1, 425 MB to 29 MB, peak host memory 14.1 GB to 11.9 GB; CPU video-writing 8.8x at 16 sections with byte-identical output |
| **libcst 1.9 (third party), `parse_module`** | `parse = 122,714*n_terms + 1,034.9*n_terms_sq + 2,100,550`, 3.7% irregular; CPython's own parser is linear on the identical text | cProfile sees only one opaque native call; drperf attributes the quadratic term across the language boundary to `DeflatedExpression::clone` in the Rust extension, which is rust-peg seed-growing on nine left-recursive grammar rules | measured: three rule families rewritten as left folds; quadratic coefficient 1,034.9 to -0.134 and 8,458.1 to 0.639; a 1,600-link chain 4,505ms to 44ms (**102x**), a real 562-file corpus 14.560s to 11.912s (-18.2%); upstream suite 1,160 pass and 562 files give identical CSTs |
| sqlglot 30.18 (third party), `optimize` | `optimize = 10,950,467*n_joins + 484,257*n_joins_sq + 87,961,347`, 1.7% irregular; fitted on 10-80 joins it predicts 160 and 240 joins to +0.9% and +0.6% | the quadratic term passes the linear one at 23 joins; 96.2% of the walking is one rule, `merge_subqueries`, undoing the single-use CTEs that `isolate_table_selects` created one per joined table | not fixed, deliberately: the invalidation is real and removing it is a redesign across six merge helpers. Measured instead: dropping the rule is 2.2x at 40 joins and 6.8x at 240, at the cost of verbose output; upstream baseline 19,422 subtests recorded for whoever attempts it |
| spec2lean (agent-written), `index tree` | one fit per document: `print_tree = 7,854,576*n_nodes` at 0.2% in a 10,684-node index, `17,930,326*n_nodes` at 0.0% in a 24,352-node one; a joint fit is refused with a negative constant | the slope ratio 2.283 matches the document ratio 2.279, so printing one heading costs a pass over the whole document: the child query filters `parent_id` but the only index is `(document_id, parent_id, ordinal)`, so the plan is SCAN plus a temp B-tree | measured: naming `document_id` makes it SEARCH; slope 17,930,326 to 109,027 and the document dependence gone (ratio 1.053); `index tree` 73.17s to 0.69s (106x), `index subtree` 102x, `index validate` 21x and `index build` 18x after the same loop found a second quadratic (an XPath rescan, 5,617 instructions per anchor-element pair); output, semantic digest and every content table identical |
| Kimi Code CLI, running | `estimate_request_tokens = 7,894.7*n_msgs + 437.5*n_chars + 270,272.8*n_tools + 1,967,904.9`, 0.1% irregular | 437.5 instructions per character of conversation on every step, because a token estimate counts characters in a Python loop; 270k per tool per step to re-serialise schemas that never change | measured: same formula re-derived after the fix gives 0.371 per character (1,179x) and 16,101 per tool (16.8x); region -98.7%, process -31.6%, session wall clock 5.62s to 4.43s (-21.1%), request bodies identical |
| Kimi Code CLI, cold start | `load_tools = 40,976,735*n_tools + 67,426,198` at 8.8% for the first seven tools, then 89.6% irregular: the count is the wrong state, the per-call region names the two tools that cost | a file-reading tool imports the OpenAI SDK (495 modules), a URL fetcher imports an HTML-extraction stack (166), the toolset imports the whole MCP package for one helper, and every tool's schema is re-validated against the meta-schema | measured: four one-line edits, 8.66G to 4.06G instructions (-53.0%) and 2.083s to 0.923s cold start (-55.7%), tool schemas and all four call sites byte-identical |
| vLLM F, prefix caching | `kv_cache_full_blocks = 7,267*num_new + 4,521`, 7%; relation `kv_tokens = admitted + generated - freed` | a block hash is three copies and two CPython hashes; the no-op per-token hasher call costs more than the hashing | measured: no-op calls gone (-993 each), -5.9% per block; the block's cost is pickle+sha, not copies; prefix rescan memoised, 70% to 8.8% and 22.8k to 6.8k per step |

## Reproduction

Everything runs on this machine (no GPU). Three builds of the extension exist,
each in its own venv, all built with the `perfmark` cargo feature so the Rust
markers are live:

| build | tree | what it is |
|---|---|---|
| `vllm-ditto/.venv-perf` | `vllm-ditto`, branch `cases` (edfb2d4) | HEAD of the annotation branch plus one whole-function marker `ftl_directory_bind_batch(requests, blocks, superblocks, rehash)`, a re-declared `ftl_directory_bind_commit(requests, superblocks, rehash)`, a `perfmark`-gated tombstone counter on `DirectoryState`, and the case drivers under `examples/cases/`. No behaviour change: this is the baseline for the fix round. (`out/bind_grow_new*` were run at f2d79ae, before `rehash` was declared; `out/bind_grow_new_rh*` at 80c348c.) |
| `old-bind/.venv-old` | `old-bind`, detached at bc77bc3 (= `d94b71d^`) | the core before the `bind_batch` rewrite of d94b71d, plus the same whole-function marker; nothing else changed |
| `fix-lookup/.venv-fix` | `fix-lookup`, branch `case-lookup-fix` (8ecd322) | verification experiment only: branch `cases` plus the change predicted in case 2, built to check the prediction; not a proposed fix |
| `fix-hashmap/.venv-hm` | `fix-hashmap`, branch `case-hashmap` (8e5349c) | verification experiment only: branch `cases` with `superblocks` keyed by `HashMap`, built to test the case 3 hypothesis |

Build recipe (`build_ext.sh TREE VENV`): maturin with `--features perfmark
--compatibility linux` and `RUSTFLAGS="-C link-arg=-Wl,-rpath,/home/ubuntu/drperf/build"`;
the `perfmark` crate links `libperfmark.so` dynamically, so maturin's manylinux
repair has to be skipped and the rpath baked in.

Runner (`run_case.sh NAME PYTHON DRIVER [--regions R,..]`): runs the driver under
`drperf-dev run --blocks`, then saves `derive`, `learn` and `trace` output under
`out/NAME/`. The commands quoted below are what it runs, with
`PYTHONPATH=/home/ubuntu/drperf-cases/vllm-ditto:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build`
and the working directory `vllm-ditto`:

```
/home/ubuntu/drperf/bin/drperf-dev run --blocks -q -o out/NAME -- PYTHON examples/cases/DRIVER.py
/home/ubuntu/drperf/bin/drperf-dev derive out/NAME [--region R] [--top N] [--predict out/OTHER]
/home/ubuntu/drperf/bin/drperf-dev learn  out/NAME
/home/ubuntu/drperf/bin/drperf-dev trace  out/NAME [--region R] [--limit N] [--check "A.x == count(B) - cum(C.y)"]
```

Every driver begins with a stateless region so that the first trigger of the
run, which late attach records without its states, cannot collide with a
region that declares some. All `out/*` directories referenced below are kept.

## How far each formula can be trusted

The cases lean on different regions, and their quality differs. Unexplained
share as reported by `derive`, in the run each case quotes:

| region | unexplained | used for |
|---|---|---|
| `ftl_directory_stats` | 0.0% | case 1 |
| `ftl_directory_lookup` | 0.0% | case 2 |
| `ftl_directory_superblock` | 0.0% | case 2 |
| `case_admission_limit` | 2.2% | case 1 |
| `case_plan_load` | 9.7% | case 2 |
| `ftl_controller_stats` | 9.8% | case 4 |
| `ftl_directory_invalidate` | 14.7% | case 1 |
| `case_count` | 22.8% | case 4 |
| `ftl_directory_bind_commit` / `bind_batch` | 62-70% | case 3 |

Cases 1, 2 and 4 rest on formulas at or under 23% unexplained and their
coefficients can be read as cost models. Case 3's region is the exception and
is treated as one: its numbers come from measured per-call totals, and the
formula is used only for the shape of the difference between two
implementations. Case 3 records what was tried to bring it down and why it
cannot come down.

## The lesson that generalises

Of the seven declarations tried on the hard region, none moved it. What moved
it was the driver: repeat every state point, keep points at exact values rather
than buckets, do not mix two code paths in one region, and drop states that are
confounded with the one you care about. A high unexplained share is first
evidence about how the region was exercised, and only then about the code.

## Findings for the fix round

No optimisation is applied on the baseline (branch `cases`). The two
experiment branches only exist to check that the predictions below hold; the
fix round should start from `cases` and re-run the same drivers, so each
change can be judged against its saved baseline in `out/`.

| # | where | cost function and the state that drives it | predicted benefit at production shape | suggested change (not made) | verify with |
|---|---|---|---|---|---|
| 0 | `compaction.py:231` `_ordered_blocks`, via the `PySuperblock.blocks` getter | `2,050*nblocks + 417*nblocks^2 + 4,943`: the getter clones and converts the whole block map per offset | ~443k per call at 32 io-blocks (497k to 54k), at least twice per completed superblock; the largest item found | read the getter once (or expose an ordered-blocks accessor from Rust) | `ordered_blocks.py`, baseline `out/ordered_blocks` (case 6) |
| 0b | `handle_manager.rs:453` `alloc_row_slot` via `ensure_row` | `35.1*full_slabs + 381*new_slab + 2,397`: the slot search walks every exhausted slab; nothing marks this path | ~17k per stored row at a full pool of 480 slabs, ~540k per 32-row store, from 0 when empty: a regression that arrives with occupancy | keep only non-full slabs in the searched list | `ensure_row_slabs.py`, baseline `out/ensure_row2` (case 7) |
| 0a | `compaction.py:253` `_clear_digests` via `_drop_key` | `288.4*digests + 7,395` per block dropped: the whole digest table is copied and compared per retired block | ~1.1M per retired block at ~3,800 digests, ~35M per retired superblock; the largest per-event cost found | key -> identities index | `digest_scan.py`, baseline `out/drop_key` (case 8) |
| 1 | `lib.rs` `PyFTLController::count` | `1,897*entries + 1,060` per call, `entries` = distinct counters in the stats dict (~30 at steady state), so ~58k per `ftl.count()`; bumped up to several times per load job and compaction | ~55k per call removed; the largest of the small items | keep counters in Rust, build the dict on read | `count_stats.py`, baseline `out/count_stats` (case 4) |
| 2 | `controller.rs` `plan_load`, `invalidate_checked`, `bind_store_batch` | `44.9*fill` per `Directory::lookup`/`superblock` call, `fill` = resident io-blocks of the touched superblock; callers pay 4, 4 and 1 of these per request in the driver | ~140k per 96-block load; ~24k per retired superblock; 1.4k per trigger key | a lookup that returns key, offset, handle, position base and flags without cloning the block map; the three sites use it | `lookup_sites.py` with `PERFMARK_NO_EXT=1`, baseline `out/lookup_sites_noext`; every `fill` coefficient should read 0 (case 2; verified on the experiment branch) |
| 3 | `directory.rs` `DirectoryState::superblocks: BTreeMap<String, _>` | the ~70% of the commit pass that follows no declared state and cannot be made to: `memcmp` under `apply_batch`, three string-keyed lookups per request per pass, cost set by the occupancy of the node the key lands in. Four declarations were tried; none moved the share (case 3) | 377k -> ~304k per 32-block bind (mean over 120 binds); the climb with directory size disappears | key the map by hash (or an interned id); keep `insertion_order` for order | `bind_grow.py`, baselines `out/bind_grow_new_rh`, `out/bind_grow_new_rh_prod` (case 3; verified on the experiment branch) |
| 4 | `directory.rs` `bind_batch` discover + rollback passes | `4,090*requests` per bind on the current core vs `1,899*requests` on the old one: the discover pass and its rollback are more than half of the per-request cost | up to ~2k per request, ~60k per 32-block bind | compute the new keys read-only (bind targets against the live state plus a set of keys created in this batch) instead of apply-then-undo | `bind_grow.py`, same baselines; the `requests` coefficient is the number to watch |
| 5 | `directory.rs` `block_locations` growth | 187 per re-hashed block at each doubling of the block index: a single bind of ~1M at 3,584 blocks, and the doubling point moves with the per-process hash seed | removes the spikes (700k at 3,584 blocks), not the mean | pre-size the index from the admission limit, or reserve per batch | `bind_grow.py` production shape; the spike binds in the trace |
| - | `controller.rs` `admission_limit` per step | `23.3*superblocks + 3,331` per step; `superblocks = count(bind_commit) - cum(invalidate.frees)` | ~6k per step at 120 superblocks: not worth a change | none | case 1 |
| - | `directory.rs` `prune_empty_logged` | `7.9*superblocks` per invalidate, `133*superblocks` per bind | ~3k and ~50k at 400 superblocks: not worth a change | none | case 1 |

---

## Case 1. The per-step admission limit: 23 instructions per resident superblock, and the relation that says what "resident" is

**The item.** The fixes list says: "admission limit recomputed every step
(`directory.stats()` full scan + Python callback) ... ~50 us per step; change:
recompute only when rows were allocated or freed since the last step." The
connector calls `ftl.admission_limit()` once per scheduler step
(`connector.py:build_connector_worker_meta` -> `controller.rs:admission_limit`
-> `directory.rs:stats`), and `stats()` walks every superblock to count the
complete ones.

**What was measured.** `examples/cases/step_admission.py` plays the production
loop: one store per step while the pool fills (each store completes a 32-block
superblock), one `admission_limit()` per step, then one superblock retired per
step until the pool is empty. The Python region `case_admission_limit(superblocks)`
wraps the whole per-step call (pyo3, the scan, the `additional_capacity`
callback); the Rust region `ftl_directory_stats(superblocks)` is the scan alone.

```
./run_case.sh step_admission vllm-ditto/.venv-perf/bin/python examples/cases/step_admission.py
```

```
derive case_admission_limit
  cost(superblocks) = 23.3*superblocks + 3,330.7        [all superblocks]   blocks: 6 affine, 924 constant, 15 irregular (2.2% of cost)
    per-superblocks coefficient by function:
                23.3  <_ditto_ftl_core::directory::Directory>::stats  [_ditto_ftl_core.abi3.so]
    constant by function:
               556.1  _PyEval_EvalFrameDefault  [python3.12]
                 328  <core::hash::sip::Hasher<core::hash::sip::Sip13Rounds> as core::hash::  [_ditto_ftl_core.abi3.so]
               325.1  _int_free  [libc.so.6]
               279  <std::hash::random::RandomState as core::hash::BuildHasher>::hash_one:  [_ditto_ftl_core.abi3.so]

derive ftl_directory_stats
  cost(superblocks) = 23.3*superblocks + 990.4        [all superblocks]   blocks: 6 affine, 138 constant, 0 irregular (0.0% of cost)
```

The same driver at production size (`CASE_SUPERBLOCKS=120`, `out/step_admission_120`):

```
derive ftl_directory_stats
  cost(superblocks) = 26.8*superblocks + 955.5        [all superblocks]   blocks: 10 affine, 136 constant, 0 irregular (0.0% of cost)
```

Per-call cost of the whole per-step call in that run, superblocks 1..120 in
order (from `drperf-dev trace out/step_admission_120 --region case_admission_limit`),
markers included:

```
6,084  5,929  5,402  5,427  5,773  5,482  5,507  5,527  5,830  5,646
...
8,208  8,233  8,258  8,283  8,308  8,452  8,380  8,405  19,776  8,455
8,480  8,505  8,552  8,577  8,602  8,627  8,652  8,677  8,702  8,749
9,217  9,229
```

**The relation.** `learn` reports, exactly at every one of the 96 admission
checks and every one of the 1,536 invalidations:

```
exact (96/96): ftl_directory_stats.superblocks = last(case_admission_limit.superblocks)
exact (96/96): case_admission_limit.superblocks = count(case_admission_limit) -2*cum(ftl_directory_invalidate.frees) +1
exact (1536/1536): ftl_directory_invalidate.superblocks = - cum(ftl_directory_invalidate.frees) +48
```

and the form one would write down by hand holds too:

```
$ drperf-dev trace out/step_admission --limit 0 \
    --check "ftl_directory_stats.superblocks == count(ftl_directory_bind_commit) - cum(ftl_directory_invalidate.frees)"
check ftl_directory_stats.superblocks == count(ftl_directory_bind_commit) - cum(ftl_directory_invalidate.frees): 96/96 triggers satisfy it
```

That is: the state the scan's cost follows is the number of superblock commits
minus the number of invalidations that emptied a superblock. Nothing in the
connector, which is where the "fix" would be written, knows either number.

**What it changed.** The item comes off the list. At 120 resident superblocks
the whole per-step call is about 6,200 instructions net of markers (measured
8.2k-8.7k with 2.2k of marker cost), and at the document's "few hundred" it is
under 14k. Whatever the 50 us per step is, it is not the scan: a fix that
recomputes the limit only when rows change can save at most this. The per-step
cost is a known function of a quantity the relation ties to stores and
retirements, so it can be sized for any deployment without running it.

Two other scans over the same state, from the same runs, for completeness:

```
derive ftl_directory_invalidate           (out/step_admission)
  cost(superblocks, frees) = 7.9*superblocks + 2,708.1*frees + 2,184.4   blocks: 423 affine, 297 constant, 14 irregular (14.7% of cost)

derive ftl_directory_bind_batch           (out/bind_grow_new, whole bind, current core)
  cost(requests, blocks, superblocks) = 4,089.8*requests + -5.4*blocks + 133.5*superblocks + 12,390.7
    per-superblocks coefficient by function:
                68.5  <alloc::collections::btree::map::Iter<alloc::string::String, _ditto_ft  [_ditto_ftl_core.abi3.so]
                20.3  <_ditto_ftl_core::directory::Directory>::apply_batch  [_ditto_ftl_core.abi3.so]
```

`prune_empty_logged` is run once per invalidate (7.9 per superblock) and twice
per bind (the discover and commit passes; 133.5 per superblock, mostly the
B-tree iterator). The fixes document calls this "a few hundred, cheap"; the
formulas agree and put a number on it: about 3k per invalidate and 50k per bind
at 400 superblocks. Not a priority either.

---

## Case 2. Three call sites clone the superblock they only read a key from: the formula sizes the fix an order of magnitude below the estimate, and the fix lands where predicted

**The item.** The fixes list says: "`plan_load` clones a `Superblock` per
requested io-block (`controller.rs:303-334`), 0.3-0.5 ms per load; change: look
up once per superblock." The annotation log's own case found this clone
(`Directory::lookup` returns a clone of the `Superblock`, whose `blocks`
B-tree holds one entry per resident io-block) and measured it in `plan_load`.

Reading the callers shows two more sites doing the same thing for the same
reason, a key or two booleans:

- `controller.rs:invalidate_checked` calls `lookup()` per invalidation to compare `superblock.key` with the expected key;
- `controller.rs:bind_store_batch` calls `directory.superblock(key)` per trigger key to read `complete()` and `gc_eligible`.

**What was measured.** `examples/cases/lookup_sites.py` builds one directory
per fill in (8, 16, 32, 64, 128, 256), and at a fixed 4 requests per call
measures each site in a Python region declaring `fill`. The invalidations carry
a wrong key so nothing is applied; the bind re-binds an existing block at its
own offset so the fill is unchanged; the directory is therefore identical at
every repetition.

```
PERFMARK_NO_EXT=1 ./run_case.sh lookup_sites_noext vllm-ditto/.venv-perf/bin/python examples/cases/lookup_sites.py
```

(`PERFMARK_NO_EXT=1` selects the ctypes marker path; see the drperf notes at the
end for why.) The primitive, from `out/lookup_sites`:

```
derive ftl_directory_lookup
  cost(fill) = 44.9*fill + -221.4        [all fill]   blocks: 55 affine, 134 constant, 0 irregular (0.0% of cost)
    per-fill coefficient by function:
                20.6  <alloc::collections::btree::map::BTreeMap<_, _, _> as core::clone::Clo  [_ditto_ftl_core.abi3.so]
                16.1  _int_malloc  [libc.so.6]
                 6.7  __GI___libc_malloc  [libc.so.6]
                 1.5  __rustc::__rdl_alloc  [_ditto_ftl_core.abi3.so]

derive ftl_directory_superblock
  cost(fill) = 44.1*fill + -108.7        [all fill]   blocks: 50 affine, 140 constant, 0 irregular (0.0% of cost)
```

and the three callers, at 4 requests (`out/lookup_sites_noext`):

```
derive case_plan_load            cost(fill) = 167.6*fill + 3,025.1
derive case_invalidate_validate  cost(fill) = 164.7*fill + -22,800.7
derive case_bind_trigger         cost(fill) =  46.3*fill + -19,980.3
```

167.6 per resident block for `plan_load`, against 4 x 44.9 = 179.6 for its
four lookups alone: the shortfall, and the fifth copy `plan_load` makes when it
groups by superblock, sit in the run's irregular share (9.7% in the fast-path
run `out/lookup_sites`, slope 165.5; 32.8% here), allocator work the fit
declined to attribute. 164.7 is the four lookups of `invalidate_checked`; 46.3
is the one `superblock()` call of a single-key bind. The
coefficient is the clone, per resident io-block, and the fixed cost of a call
does not depend on fill at all.

**The prediction.** A load of 96 io-blocks out of 32-block superblocks pays
96 x 44.9 x 32 = 138k instructions for the clones, plus 3 x 1.4k for the
grouping copies. That is roughly 45 us if one takes 3 instructions per ns as
the order of magnitude, not 300-500 us. `invalidate_checked` on a retiring
superblock pays 44.9 x (32 + 31 + ... + 1) = 24k. The bind check pays 1.4k per
trigger key. Removing the clones should set the `fill` coefficient of all
three sites to zero and change nothing else.

**The change.** Branch `case-lookup-fix` (8ecd322, 41 lines added in
`directory.rs`, 39 changed in `controller.rs`): `Directory::locate(logical_block)`
returns key, offset, handle, position base and the two flags without touching
the block map; `Directory::is_trigger_candidate(key)` returns the two booleans;
the three sites use them. Same driver, same command, on `fix-lookup/.venv-fix`
(`out/lookup_sites_fix`):

```
derive case_bind_trigger         cost(fill) = 0*fill + -26,148.8    blocks: 0 affine, 2347 constant, 0 irregular
derive case_invalidate_validate  cost(fill) = 0*fill + -11,387.3    blocks: 0 affine, 1138 constant, 0 irregular
derive case_plan_load            cost(fill) = 0*fill + 877.3        blocks: 0 affine, 1960 constant, 51 irregular (77.9% of cost)
    irregular blocks, per call: 1,032 .. 13,317.4
```

(The negative constants are the ctypes marker cost being over-subtracted; only
the slopes are compared here. The remaining `plan_load` irregularity is
allocator noise on a call that is now a few thousand instructions in total.)

Functional check, `examples/cases/equivalence.py`, a seeded 400-step random
workload of binds, loads with unmapped blocks and checked invalidations with
stale keys, hashing every plan and result; identical on the unfixed, fixed and
pre-rewrite cores:

```
digest c4529c2f9fbf6a75 stats [('blocks', 28), ('complete', 0), ('superblocks', 25)] counters [('loads', 0), ('stores', 183), ('unmapped', 90)]
```

**What it changed.** The estimate on the list was ten times too high, the fix
is worth about 140k instructions per full-context load, it exists, and the same
change also covers two sites the list did not mention. The formula told which
number to expect before the code was touched: the per-fill slope of each site
is an integer multiple of the primitive's slope, so a reader can see how many
clones each path does without reading it.

---

## Case 3. Two `bind_batch` implementations: at the scale of the drivers the old one wins, at production it loses 8x, and the cost functions say why

**The item.** Commit d94b71d rewrote `Directory::bind_batch`: the previous
version cloned the entire `DirectoryState` (every superblock with its block
map, plus the block index) to plan a batch on the copy and swap it in; the
current version mutates in place under an undo log, in two passes (discover,
roll back, allocate handles, commit). The fixes document records this as done:
"no more clone of the whole `DirectoryState` per store job".

**What was measured.** The pre-rewrite core was rebuilt from `d94b71d^` with
one marker added at the top of `bind_batch`, `ftl_directory_bind_batch(requests,
blocks, superblocks)`, and the same marker was added to the current core (branch
`cases`). `examples/cases/bind_grow.py` grows one directory a superblock per
bind: 24 binds of 4 blocks, then 24 of 16, so `blocks` and `superblocks` do not
move in step and can be separated. Both cores, same driver:

```
./run_case.sh bind_grow_old old-bind/.venv-old/bin/python   examples/cases/bind_grow.py --regions ftl_directory_bind_batch
./run_case.sh bind_grow_new vllm-ditto/.venv-perf/bin/python examples/cases/bind_grow.py --regions ftl_directory_bind_batch
```

```
old (clone the state):
  cost(requests, blocks, superblocks) = 1,898.6*requests + 329.7*blocks + 946.6*superblocks + 6,788.1   blocks: 424 affine, 1073 constant, 147 irregular (41.7% of cost)
    per-blocks coefficient by function:
                83.5  _int_free  [libc.so.6]
                  36  __free  [libc.so.6]
                  34  <hashbrown::raw::RawTable<(i64, (alloc::string::String, usize))> as co  [_ditto_ftl_core.abi3.so]
                  33  <alloc::string::String as core::clone::Clone>::clone  [_ditto_ftl_core.abi3.so]
                29.6  __GI___libc_malloc  [libc.so.6]
                22.2  <alloc::collections::btree::map::BTreeMap<_, _, _> as core::clone::Clo  [_ditto_ftl_core.abi3.so]
    per-superblocks coefficient by function:
               244.2  _int_free  [libc.so.6]
               109.1  __free  [libc.so.6]
                  99  <alloc::string::String as core::clone::Clone>::clone  [_ditto_ftl_core.abi3.so]
                87.5  __GI___libc_malloc  [libc.so.6]
                72.6  <alloc::collections::btree::map::BTreeMap<_, _, _> as core::clone::Clo  [_ditto_ftl_core.abi3.so]
    irregular by function:
            35,898.8  _int_malloc  [libc.so.6]

new (undo log):
  cost(requests, blocks, superblocks) = 4,089.8*requests + -5.4*blocks + 133.5*superblocks + 12,390.7   blocks: 413 affine, 1233 constant, 150 irregular (52.4% of cost)
    irregular blocks, per call: 13,815 .. 143,625.5
    irregular by function:
            15,606.8  __memcmp_avx2_movbe  [libc.so.6]
            14,455.3  <_ditto_ftl_core::directory::Directory>::apply_batch  [_ditto_ftl_core.abi3.so]
             7,953.9  _int_malloc  [libc.so.6]
```

The old formula is the clone: 330 per resident io-block and 947 per superblock,
attributed to `String::clone`, `BTreeMap::clone`, the hash-table clone and the
matching frees, on every bind, whatever its size. The new formula has no
per-block term, a small per-superblock term (the prune scan, case 1), and a
per-request cost more than twice the old one: the two passes plus the undo log.

**Alike at small scale.** Per-call cost from the traces of the same two runs,
requests = 4, superblocks 0..9 (`drperf-dev trace out/bind_grow_{old,new} --region ftl_directory_bind_batch`):

```
superblocks:   0       1       2       3       4       5       6       7       8       9
old         19,393  24,969  25,787  33,570  34,822  39,471  43,127  55,707  53,039  56,750
new         47,418  47,552  46,233  52,888  48,784  50,759  52,511  62,214  56,240  58,745
```

At the directory sizes of the repository's tests and annotation drivers (five
superblocks or fewer) the pre-rewrite code is cheaper. A profile of either at
that scale shows malloc, memcmp and `apply_batch`, and nothing that says one of
them grows with the directory.

**Diverging at production shape.** Same driver, 120 binds of 32 blocks
(`CASE_STEPS=60 CASE_FILL_A=32 CASE_FILL_B=32`, `out/bind_grow_{old,new}_prod`),
every eighth bind:

```
superblocks:  0        8        16       24       32       40       48       56         64         72         80         88         96         104        112
old        117,375  297,186  485,157  614,071  784,286  940,422  1,117,894  1,646,033  1,476,831  1,662,969  1,796,992  1,968,092  2,113,324  2,255,061  3,094,844
new        258,488  342,094  357,451  392,651  301,457  285,740    332,595    382,815    397,545    440,571    414,214    429,822    397,915    366,259    355,777
```

The old core's formula from the small run, evaluated at the production point
(32 requests, 3,584 blocks, 112 superblocks), gives 1,899x32 + 330x3,584 +
947x112 + 6.8k = 1.35M; the measured value is 3.09M, and `derive --predict`
says why the formula is a floor: "formula covers only 58% of this regime's
cost", the rest being the 42% of allocator work it refused to fit (running the
driver with `GLIBC_TUNABLES=glibc.malloc.tcache_count=0 MALLOC_ARENA_MAX=1`
brings that share to 28.8% and the block coefficient to 433). The direction
and the order of magnitude are what the decision needs: a bind that costs
about the same as the new one at five superblocks costs eight times more at a
hundred.

**What the rewrite left behind.** The new core's 52% irregular share is not
allocator noise (the deterministic allocator leaves it at 49.7%). It is
`memcmp` under `apply_batch`, and it follows a state the region does not
declare. From `out/step_admission` (32 requests per bind, one superblock per
bind), the commit pass alone, `drperf-dev trace out/step_admission --region ftl_directory_bind_commit`:

```
blocks:    0       32      64      96      128     160     192     224     256     288     320     352     384     416      448
commit  65,148  70,848  76,513  84,751  86,942  90,591  95,492  87,073  97,684  107,902  64,070  91,454  91,876  178,755  102,365
```

The cost climbs by 4-5k per superblock and then drops back (at 10 superblocks,
again at 25, 30, 40), with one spike when `block_locations` doubles (416+32 =
448 blocks; discover's declared `rehash` state prices that at 186.8 per
rehashed block). `superblocks` is a `BTreeMap<String, Superblock>`: every
request does three string-keyed lookups per pass, each a linear scan of one
leaf with `memcmp` per key, and a leaf holds up to eleven keys before it
splits. The cost follows the occupancy of the leaf the new key lands in, which
is why it is neither constant nor linear in anything declared: at 16
requests the same bind costs anywhere from 153k to 211k depending on where in
the leaf's fill cycle the directory happens to be.

**Could a better formula have explained it?** This was pushed until it
stopped paying, because it is the question drperf's loop is supposed to
answer: read the unexplained functions, find the state they follow, declare
it, watch the share fall. Here the share does not fall. All four
declarations below were measured on the same driver at the same production
shape (120 binds of 32 blocks, the `commit` pass), so the percentages compare
directly:

| declared states | formula | unexplained |
|---|---|---|
| `requests, blocks` (as annotated on the branch) | `1.4*blocks + 33,048` | 69.7% |
| `requests, superblocks, rank, rehash` (rank = keys sorting before the batch's target) | `50*superblocks - 9.9*rank + 0.0202*rehash + 34,603` | 71.0% |
| `requests, superblocks, headroom, tombstones` (index growth left, and entries the rollbacks removed since it last grew) | `44.1*superblocks + 0*headroom + 0*tombstones + 32,956` | 70.4% |
| `requests, superblocks, rehash` (rehash = entries moved when arrivals exceed headroom, 0 otherwise) | `44*superblocks + 0.0187*rehash + 33,162` | 69.7% |
| `requests, superblocks, searches, rehash` (searches = requests x tree depth, a product) | `45.5*superblocks + 0.434*searches + 0.082*rehash + 33,186` | 69.6% |
| `requests, resident` with `resident = superblocks/16` (coarse: no per-call-unique quantity) | `1,339.3*requests + 956.8*resident + 4,829` | **54.2%** |
| `requests, resident, rehash` (threshold added back on top of the coarse pair) | `999.6*requests + 638.5*resident + 0.552*rehash + 4,231` | 65.0% |

The three added states are each a legitimate reading of "the history that
sets the cost", and the third is carried by the program rather than projected:
`DirectoryState` gains a `perfmark`-gated counter of the entries each rollback
removes since the block index last changed capacity, because a removal leaves
a tombstone that spends the table's growth exactly as a live entry does, and
no projection from the length can see that. Every one of them is reported with
a coefficient at or near zero, and drperf is right to do so:

- `rank` is collinear with `superblocks` in this driver and its coefficient
  comes out negative, the signature of a state that is not the driver.
- `headroom` and `tombstones` describe a threshold, not a slope. The bind at
  55 superblocks runs with `headroom=14` against 32 arriving blocks and costs
  447,272 against a ~110,000 neighbour, but a plane in `headroom` cannot
  express "and then it grows".
- The indicator built for that threshold fires five times in 120 binds, at 6,
  13, 27, 55 and 111 superblocks, and the cost per entry it implies is 432,
  then 127, then 254, then 223. Not proportional, so not affine, so correctly
  left out of the coefficients.
- `searches` counts the work rather than describing it: every request makes a
  fixed number of lookups in the map and each compares keys down one
  root-to-leaf path, so the comparisons go as requests x depth. Declared as
  that product it earns 0.434 per search and moves the share by 0.1 points.

None of this is an artifact of averaging the two instrumented repeats,
which run with different hash seeds: derived from each repeat alone the
share is 70.4% and 69.4%.

Varying `requests` at production size (`CASE_STEPS=45 CASE_FILL_A=8
CASE_FILL_B=32`, `out/commit_vary_prod`) recovers the per-request coefficient
that a fixed batch size hides, `841.4*requests + 45.6*superblocks + 3,397`,
and leaves the share at 70.1%.

**What actually brought it down.** Not a better description of the work, but a
coarser one. `blocks` and `superblocks` take a new value on every single call,
so all 120 binds sat at 120 state points of one sample each, and drperf's
per-block test compares a block's cost at a point against a plane within a 5%
tolerance. With one sample per point there is nothing to average, so ordinary
allocator and hash jitter is classified irregular. Bucketing the directory
into `superblocks/16` gives about 30 binds per point, and the irregular block
count falls from 155 to 33.

What matters is where the search cost goes once the points have samples: into
the coefficients, where it belongs.

```
per-requests coefficient by function:
           370.1  <Directory>::apply_batch          <- the inlined B-tree search
           286.5  _int_malloc
           137.2  __GI___libc_malloc
per-resident coefficient by function:
           471.2  <btree::map::Iter<String, Superblock>>   <- the prune scan
           270.6  _int_malloc
             102  __memcmp_avx2_movbe               <- the key comparison
```

So the B-tree search is explainable after all, at 370 instructions per request
plus 102 per sixteen resident superblocks. It was never the search that
resisted the fit; it was asking the fit to distinguish 120 singleton points.

Adding the threshold state back on top of the coarse pair makes it worse, 65.0%,
because the indicator fires often enough to split the points into singletons
again and give back the averaging.

What is left at 54.2% is not the B-tree. It is the hash-table rehash: two binds
of 120 cost 447,272 and 793,329 against a ~110,000 neighbour, and the ratio of
those two excesses to the table size at each, 191 and 192 instructions per
entry, is the same to within a part in two hundred. The work is exactly
proportional; only its timing is not predictable, because which pass pays for
the growth depends on tombstones left by the rollback and on the per-process
hash seed. Across the two instrumented repeats of one run the spikes land on
different binds.

Correlating the measured cost against superblock count directly gives R^2 =
0.06: the commit pass is close to flat per bind, and the variance the fit was
being asked to explain was almost entirely those two events.

What is left is `memcmp` and `apply_batch`, in every attribution, in the same
proportion: the string-keyed B-tree search. Its cost per lookup is set by how
many keys sit in the node the search lands in, and that occupancy is a
function of the entire insertion and removal history of the map, which the
program can neither read nor summarise in an integer. The hash side is worse
than undeclarable, it is not deterministic: the same logical run grows the
index at different binds in the two instrumented repeats, because the
placement of tombstones depends on the per-process random hash seed.

The A/B against the hash-keyed build settles what the residue is. Same
driver, same shape, same declared states, only the key type differs:

```
BTreeMap<String, _>   cost(requests, blocks) = 1.4*blocks   + 33,048   irregular 69.7%
    irregular by function: apply_batch 25,494 | __memcmp_avx2_movbe 22,781 | hash_one 13,043
HashMap                cost(requests, blocks) = 0.491*blocks + 34,165   irregular 62.7%
    irregular by function: sip::Hasher 17,196 | _int_malloc 12,249 | hash_one 10,234
```

The `memcmp` disappears with the string keys, which is the confirmation that
it was the B-tree search, and the share barely moves because a hash table's
probe counts are just as internal as a B-tree's node fills. The residue is
container-internal work in both, which is why no declaration reaches it.

**Verdict on this region: 19.5%, under the campaign's 20% bar.** Getting there
took four fixes, and only the last one was about the marker's states.

```
$ CASE_REPEAT=1 CASE_SIZES=0 CASE_FILLS=4,8,12,16,20,24 CASE_REPS=1 CASE_INNER=150 \
    ./run_case.sh commit_pure2 .venv-perf/bin/python examples/cases/bind_at_size.py

  states: requests=4 x150, requests=8 x151, requests=12 x150, requests=16 x151,
          requests=20 x150, requests=24 x1058
  cost(requests) = 2,237.6*requests + 3,877.5        [all requests]
      blocks: 192 affine, 648 constant, 33 irregular (19.5% of cost)
```

1. **Every call sat on a state point seen once.** `blocks` and `superblocks`
   take a new value on every bind, so 120 calls made 120 singleton points. A
   point with one sample has no mean, and the 5% per-block tolerance then reads
   ordinary allocator jitter as cost that follows no state. This was the
   largest single factor and it is a property of the driver, not the code.
2. **Bucketing was the wrong repair.** `superblocks/16` bought samples, but a
   bucket spans 32 real directory sizes, so the spread inside a point became
   genuine variation. It reached 54.2% and stopped.
3. **The driver mixed two operations.** The binds that build the fixture create
   superblocks; the binds being measured replaced blocks in one. No plane spans
   two code paths. Holding the directory at an exact size and making the
   measured call create-and-prune as well reached 42.1%.
4. **Then the states mattered, and the answer was fewer.** `resident`
   oscillated with the batch size, because a partial rebind leaves the old
   superblock alive and a full one empties it. It was a confound, not a state.
   Dropping it left `requests` alone, and the region resolved.

The earlier conclusion in this section, that the cost was structurally
undeclarable, was wrong. It is 2,238 instructions per request plus 3,878, and
the B-tree search sits inside that coefficient.

**What this run does not measure.** It holds the directory at one size, so it
gives the per-request cost cleanly and says nothing about how cost varies with
directory size. Recovering both at once needs `requests` and directory size to
vary independently with every combination repeated, which is again a driver
change rather than a marker change.

 Its formula is not
a usable cost model and should not be quoted as one. What this region does
yield is the attribution, which names the same three container-internal
symbols every time, and the measured per-call totals in the trace, which are
exact. Every quantitative claim in this case rests on those totals, not on the
formula: the 1,371,318 / 377,313 / 304,471 instructions per bind are measured
means over 120 binds, and the per-call tables are raw trigger costs.

So the honest report on this region is that its cost is not an affine function
of any state the program can declare, and that this is a property of the data
structure rather than a gap in the annotation. That is the argument for the
change below, and it is one a percentage alone would not have made: the
residue is stable at 70% however it is described, and its attribution names
the same two symbols every time.

**The experiment.** Branch `case-hashmap` (8e5349c) changes the type of that
one field to `HashMap<String, Superblock>` and sorts the keys `prune_empty`
collects so the order of freed handles stays deterministic; nothing else.
Same driver, same command, on `fix-hashmap/.venv-hm`:

```
derive ftl_directory_bind_batch          (out/bind_grow_hm)
  cost(requests, blocks, superblocks) = 4,168.9*requests + -1.7*blocks + 42.9*superblocks + 11,923   blocks: 391 affine, 1179 constant, 140 irregular (46.4% of cost)
    irregular by function:
            14,088.4  <core::hash::sip::Hasher<core::hash::sip::Sip13Rounds> as core::hash::  [_ditto_ftl_core.abi3.so]
               8,090  <std::hash::random::RandomState as core::hash::BuildHasher>::hash_one:  [_ditto_ftl_core.abi3.so]
```

Per call, requests = 16, superblocks 24..33, B-tree then hash map:

```
superblocks:   24       25       26       27       28       29       30       31       32       33
BTreeMap    210,558  207,309  185,585  189,572  200,278  201,210  153,264  202,648  163,148  172,087
HashMap     183,273  158,892  163,515  169,298  163,702  155,104  155,205  155,287  190,581  158,693
```

and at production shape (`out/bind_grow_hm_prod`, every eighth bind):

```
superblocks:  0        8        16       24       32       40       48       56       64       72       80       88       96       104      112
BTreeMap   258,488  342,094  357,451  392,651  301,457  285,740  332,595  382,815  397,545  440,571  414,214  429,822  397,915  366,259  355,777
HashMap    299,841  283,599  291,148  296,532  297,995  298,143  295,231  305,432  300,170  295,840  290,025  296,024  289,175  290,663  308,353
```

The climb with the directory is gone; what remains irregular is SipHash at the
hash map's own growth points (3, 7, 14, 28, 56 keys) and the `block_locations`
doubling that every variant pays: in both production-shaped runs the binds at
55 and 111 superblocks (1,760 and 3,552 blocks, the next 32 crossing 1,792 and
3,584) cost 648k/996k with the hash map and 699k/1,066k with the B-tree, the
187 per rehashed block that the discover pass's declared `rehash` state priced.
Over the 120 production-shaped binds the means are: old core 1,371,318, current
core 377,313, hash-keyed current core 304,471 instructions per bind. The
equivalence digest of case 2 is unchanged (`c4529c2f9fbf6a75`).


**What it changed.** Three things a profiler at driver scale does not give:
the rewrite was the right call even though the small-scale numbers favour the
old code, because the old cost function has terms in `blocks` and
`superblocks` and the new one does not; the residual growth in the new one
comes from the key type of one map, not from the algorithm, and changing that
type is worth 19% of the bind at production shape (377k to 304k per 32-block
bind, more at the directory sizes where a leaf is nearly full) with a one-line
diff; and the discover pass plus rollback are more than half of the new
per-request cost, so a read-only discovery (compute the new keys without
mutating) is the next-largest saving on this path. A fourth, smaller: the
`block_locations` doubling is a single bind that costs 187 instructions per
resident block, 700k at 3,584 blocks, and could be pre-sized from the admission
limit.

---

## Case 4. `ftl.count()` round-trips the whole stats dict: 1,900 instructions per distinct counter

**The item.** The fixes list says: "`ftl.count()` pulls and syncs the whole
stats dict per call (`lib.rs:1016-1021`), 2 round trips per counter bump; keep
counters in Rust, export lazily." The binding reads every (name, value) of the
Python dict into the Rust map, bumps one counter, clears the dict and rewrites
it (`PyFTLController::pull_stats`, `sync_stats`).

**What was measured.** `examples/cases/count_stats.py`: controllers whose
stats dict holds 7, 11, 19, 35 and 67 entries; `ftl.count("stores")` ten times
each, in a Python region declaring `entries`.

```
./run_case.sh count_stats vllm-ditto/.venv-perf/bin/python examples/cases/count_stats.py
```

```
derive case_count
  cost(entries) = 1,896.6*entries + 1,060.1        [all entries]   blocks: 359 affine, 700 constant, 47 irregular (22.8% of cost)

derive ftl_controller_stats           (the Rust clone inside sync_stats only)
  cost(entries) = 315*entries + -1,154.9
    per-entries coefficient by function:
               159.5  PyDict_SetItem  [python3.12]
               150.3  <core::hash::sip::Hasher<core::hash::sip::Sip13Rounds> as core::hash::  [_ditto_ftl_core.abi3.so]
               143.5  _int_free  [libc.so.6]
               113.8  _int_malloc  [libc.so.6]
```

**What it changed.** The source defines 27 distinct counter names on the
Python side plus the core's own, so a steady-state dict has about 30 entries
and one `count()` costs about 58k instructions. The worker bumps up to several per
load job (`load_partial_io`, `decode_submitted_rows`, the decode backlog
counters) and the compaction engine several per compaction. That puts this
item above the `plan_load` clone (138k per load, case 2, now fixed) once two or
three counters are bumped per job, and far above the admission scan (case 1).
The list's order was admission, plan_load, count; the formulas say count,
plan_load, and drop admission. The fix is mechanical: keep the counters in
Rust and materialise the dict on read.

---

## Case 5. A container's internal state, in 40 lines of Python

`examples/hashmap_internal.py` isolates the mechanism behind case 3's residue
with a CPython dict. Two regions declare what the caller knows, `n` operations
against a dict of `size` entries:

```python
with region("hm_lookup", n=n, size=size):
    for k in keys[:n]:
        d[k]
with region("hm_insert", n=n, size=size):
    for j in range(n):
        d[f"new-{j}"] = j
```

```
hm_lookup   cost(n, size) = 768.7*n   + 0*size + 1,298.9     0.0% irregular
hm_insert   cost(n, size) = 1,970.2*n + 0*size + 2,624      10.6% irregular
    irregular by function: PyDict_Contains 2,020 | PyDict_SetItem 1,293 | _Py_HashBytes 672
```

`size` has coefficient 0 in both: an operation costs the same in a dict of 40
or 300. The insert residue is the resize, and the per-point means show it as a
step at the sizes whose table happens to be near 2/3 load (80, 160, 340), not
as a slope. The table's headroom is internal to the dict, the exact analogue
of node fill in the B-tree.

Declaring it is possible here because a resize is observable from outside: a
copy's byte size changes exactly when its table is rebuilt.

```python
probe = dict(d); before = sys.getsizeof(probe)
for j in range(n): probe[f"new-{j}"] = j
rehash = size if sys.getsizeof(probe) != before else 0
with region("hm_insert", n=n, size=size, rehash=rehash): ...
```

```
sizes 40..340,  n 8..32:   cost = 2,014.7*n + 5*rehash   + 2,518    6.6% irregular
sizes 20..1500, n 4..64:   cost = 1,957.8*n + 1.7*rehash + 1,428   10.5% irregular
```

Widening the sweep is the check on any such declaration. The workload term
holds (2,015 to 1,958 per insert; the small run predicts the large one within
7%), and the internal-state term does not (5 to 1.7 per entry), because
"entries moved" is a proxy for a cost that is really the new table's slot
count plus a reinsert. A coefficient on a proxy for hidden state is only as
good as the range it was fitted on, and drperf's `--predict` across runs is
what says so.

---

## Case 6. A hidden quadratic: `_ordered_blocks` clones the block map once per offset

**Where.** `CompactionEngine._ordered_blocks` (`src/integration/vllm/compaction.py:231`)
builds the ordered tuple of a superblock's blocks as
`tuple(int(superblock.blocks[offset]) for offset in range(superblock.nblocks))`.
`superblock.blocks` is a pyo3 getter (`lib.rs:682`) that clones the Rust
`BTreeMap` and converts it to a new Python dict on every access, so the
generator pays one full clone-and-convert per offset: n io-blocks cost n
clones of n entries. It is called from `trigger` (per key), `_candidate`,
`_witness_matches` and `record_bind_digest`, and in three of those four it
runs before the caller's marked region opens, so none of the campaign's
regions ever saw it, and none of them declares `nblocks`.

**What was measured.** `examples/cases/ordered_blocks.py`: one complete
superblock per size in 4..64, twenty calls each, in two regions that both
declare `nblocks` and its square: the real function, and the same loop with
the getter read once, as a prediction and not a change to the code.

```
CASE_REPEAT=1 ./run_case.sh ordered_blocks vllm-ditto/.venv-perf/bin/python examples/cases/ordered_blocks.py

case_ordered_blocks   cost(nblocks, square) = 2,049.7*nblocks + 416.9*square + 4,942.8    (16.1% irregular)
    per-square coefficient by function:
               127.4  PyDict_SetItem
                  55  PyDict_Contains
                45.2  <btree::map::IntoIter<usize, i64>>::dying_next
                  26  PyLong_FromLong
case_ordered_once     cost(nblocks, square) = 1,499.7*nblocks + -0.196*square + 6,363.1   (1.3% irregular)
```

The square term is the clone: 417 instructions per offset-times-entry, and
its attribution is the dict being rebuilt (`PyDict_SetItem`) from the
consumed Rust map (`IntoIter::dying_next`). Read the getter once and the
square coefficient is zero to three decimals.

**What it changed.** At the production superblock of 32 io-blocks the real
call costs about 497k instructions and the one-read form about 54k, nine
times less, for the same tuple. `trigger` and `_candidate` run it once per
completed superblock and `_witness_matches` once per candidate, so a store
that completes a superblock pays it at least twice. This is the largest
single item found on the branch, and it was invisible to the annotation
campaign for a reason worth recording: the regions were placed after the
call, and its cost follows a state (`nblocks`) that no caller thought of as
varying, because in production it never does. A flat state can still be the
one that squares.

It is also the cleanest demonstration here of a computed state: `nblocks`
alone reports a negative constant and an irregular share; declaring the
product `nblocks*nblocks` alongside it makes the region affine with the
square carrying the cost.

---

## Case 7. `ensure_row` walks every exhausted slab: a cost that grows as the pool fills

**Where.** `HandleManager::alloc_row_slot` (`rust/ditto-ftl-core/src/handle_manager.rs:453`)
finds a slot for a new io-block row by walking `slabs_by_size[row_bytes]` in
order and looking each slab up in a B-tree to ask whether it still has a free
slot. A full slab leaves that list only when its last row is freed
(`reclaim_row_slot`), so the prefix of exhausted slabs grows by one for every
slab the pool fills, and every row a store materialises walks all of them.
`ensure_row` carries no marker on the branch.

**What was measured.** `examples/cases/ensure_row_slabs.py`: one handle of 240
rows, four rows per slab, `ensure_row` on each row in turn inside a Python
region declaring the number of slabs already full, and whether this row is the
first of a new slab. Six rebuilds, so every point repeats.

```
CASE_REPEAT=1 ./run_case.sh ensure_row2 vllm-ditto/.venv-perf/bin/python examples/cases/ensure_row_slabs.py

case_ensure_row   cost(full_slabs, new_slab) = 35.1*full_slabs + 381.2*new_slab + 2,397.2   (35.1% irregular, 3 blocks, 272..4,442 per call)
    per-full_slabs coefficient by function:
                33.8  <ManagerCore>::alloc_row_slot
                 1.3  <ManagerCore>::row_slot_start
    per-new_slab coefficient by function:
               320.2  <ManagerCore>::alloc_row_slot
                  29  <btree::node::Handle>...
```

35 instructions per exhausted slab, all of it in `alloc_row_slot`: the walk.
The residue is the slab index's own growth (a `Vec` doubling and B-tree
inserts on the slab-creation path), bounded at 4.4k per call and not the
point.

**What it changed.** In production a raw fp8 row of a 7B model is about 7 MB
and the store chunk is 2 MiB, so rows exceed a chunk and a slab holds
`LARGE_SLAB_ROWS = 8` of them. A full pool of 40 sessions x 96 io-blocks is
3,840 rows, 480 slabs, so the last rows stored pay about 17k instructions
each in this walk, and a 32-row store about 540k, up from nothing when the
pool was empty. The formula makes that a prediction rather than a discovery:
cost per stored row is `35 x (resident rows / 8)`, linear in pool occupancy,
which is the regression an engineer would see only after the pool had been
running long enough to fill. The fix is a free-list of non-full slabs, or
removing a slab from the list when it fills; either makes the coefficient 0.

A second walk sits behind it and was not measured: `new_slab` calls
`find_run`, which scans the free chunk set for a contiguous run, 28 chunks for
an 8-row slab of 7 MB rows. That is constant while the pool only grows and
becomes a scan of the whole fragmented free set once rows are freed and
re-allocated. A driver that frees and refills would be the next measurement.

---

## Case 8. `_clear_digests` copies the whole digest table for every retired block

**Where.** `CompactionEngine._drop_key` (`src/integration/vllm/compaction.py:258`)
calls `_clear_digests`, which does `for identity in tuple(self.digests)` and
compares every identity to the key. `invalidate_blocks` calls `_drop_key`
once per retired or rebound block, so retiring b blocks scans the whole table
b times. The branch's region declares `blocks` only, and its driver seeds one
digest per block, so the table's size moved in step with `blocks` and the
scan hid inside the per-block slope (16,735 per block in the sweep).

**What was measured.** `examples/cases/digest_scan.py`: a digest table of
32..4,096 unrelated entries plus one per victim, and `_drop_key` on each
victim in a region declaring the table size (why not `invalidate_blocks`
itself is in the drperf notes below).

```
CASE_REPEAT=1 CASE_BLOCKS=1 CASE_DIGESTS=32,64,128,256,512,1024,2048,4096 CASE_REPS=10 \
  ./run_case.sh drop_key vllm-ditto/.venv-perf/bin/python examples/cases/digest_scan.py

case_drop_key   cost(digests) = 288.4*digests + 7,395.3        [all digests]   0.0% irregular
    per-digests coefficient by function:
                 211  _PyEval_EvalFrameDefault
                  47  PyDict_Clear
                  11  PySequence_Tuple
                   8  _PyUnicode_Equal
```

288 instructions per entry in the table, per block dropped, the interpreter
running the comparison loop. A native timing agrees: `invalidate_blocks` of 8
blocks takes 28 us against 64 digests, 123 us against 512, 881 us against
4,096.

**What it changed.** The digest table holds one entry per bound io-block on
the worker, about 3,800 at the documented pool, so every block retired or
rebound costs about 1.1M instructions here, and a 32-block superblock about
35M, on the store path. That is the largest per-event cost found on the
branch, and the annotation campaign's region reported it at 0% unexplained
because its driver never let the table and the batch differ. An index from
key to identities makes the coefficient zero.

---

## vLLM itself: the CPU backend under drperf

drperf's own tree holds vLLM 0.28 with the CPU backend and a marker script
for seven of its methods. That tree cannot be written from here, so the
package is copied to `vllm-cpu-src/` and put first on `PYTHONPATH`; the
editable install's finder is appended to `sys.meta_path`, so the copy wins.
`examples/vllm_run.py` is drperf's driver: `facebook/opt-125m`, bfloat16,
`max_model_len` 256, one process (`VLLM_ENABLE_V1_MULTIPROCESSING=0`).

```
export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-src:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
export VLLM_CPU_OMP_THREADS_BIND=all
/home/ubuntu/drperf/bin/drperf-dev run --blocks -q --threads 8 --repeat 1 --max-slots 2097152 \
    -o out/vllm_base -- /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run.py reqs=6
```

Native 11.5 s; instrumented from process start 300.6 s (27x). The seven
regions as drperf marks them, six requests, verbatim (`out/vllm_base/derive.txt`):

```
execute_model       cost(num_tokens, num_reqs) = 118,327,741.3*num_tokens + 55,089,773.1*num_reqs + 8,966,466.5    0.8% irregular
    num_tokens: 114,711,552 bf16_dot_with_fp32_arith | num_reqs: 53,271,936 bf16_dot_with_fp32_arith
sample              cost(num_reqs) = 704,619.7*num_reqs + 71,864.2                                                  9.9%
schedule            cost(running, waiting) = 30,746.3*running + 60,133.5*waiting + 70,403.8                        50.9%
    running: 10,988 _PyEval_EvalFrameDefault, 2,302 _PyErr_ChainStackItem, 1,771 _PyTuple_Resize
update_from_output  cost(running, num_tokens) = 9,009*running + 157*num_tokens + 42,625.4                          41.7%
attention           cost(num_tokens, kv_tokens) = 1,066.8*num_tokens + 9.7*kv_tokens + 90,701.1                    88.6%
engine_step         cost(unfinished) = 1,343,474.2*unfinished + 11,696,254                                         98.3%
generate_loop       two state points, no formula
```

Relations, exact at every trigger (`out/vllm_base/learn.txt`):

```
attention.num_tokens          = last(execute_model.num_tokens)
sample.num_reqs               = last(execute_model.num_reqs)
update_from_output.running    = last(execute_model.num_reqs)
update_from_output.num_tokens = last(attention.num_tokens)
schedule.waiting = cum(generate_loop.unfinished) + cum(schedule.running) - cum(execute_model.num_reqs)
```

The last one is the scheduler's conservation law, learned rather than
written: what is waiting is what was submitted plus what was running and not
yet executed. `execute_model` at 0.8% is the model's compute, and the
attention and engine_step residues are GEMM tiles whose block counts are not
linear in tokens; those are not the interesting regions here. The scheduler
side is: about 31k instructions per running request per step in `schedule`
and 9k in `update_from_output`, half of it following no declared state, all
of it Python bookkeeping that runs whether or not anything changed. That is
where the next markers go (below).

One trap on the way, worth its own line: the client's default slot table
(131,072 basic blocks) overflows on vLLM (~556k blocks), and every overflowed
block is credited to the last slot, so all seven regions came out 83 to 99.9%
irregular with the residue attributed to one meaningless symbol
(`TORCH_LIBRARY_IMPL_init_aten_Meta_86`). The only sign was a one-line
warning. `--max-slots 2097152` fixes it; that run is kept as
`out/vllm_base_overflow128k/` for comparison.

### vLLM case A. The scheduler side per step: a fixed tax, a step function, and a rebuild

Late attach makes vLLM measurable at will: a stateless region placed after
`LLM(...)` returns, run with `--late`, cuts the identical workload from 300.6 s
to 24.7 s (native 11.2 s), and the seven baseline formulas reproduce to within
noise (`out/vllm_late`). Five regions were then added around the per-step,
per-request paths between `schedule` and `execute_model`
(`examples/vllm_mark2.py`), and the run widened to ten requests
(`out/vllm_marked`, 27.3 s).

```
prepare_inputs        cost(num_reqs, num_tokens) = 758.2*num_reqs + 106.9*num_tokens + 464,927.7                    20.9% irregular
update_states         cost(num_reqs, num_new, num_finished) = 1,825.7*num_reqs + 27,753.1*num_new + 11,182.4*num_finished + 58,977.5   55.1%
update_from_output    cost(running, num_reqs) = 7,276.4*running + 0*num_reqs + 34,806.7                              57.7%
cached_request_data   cost(num_running, num_resumed) = 4,907.1*num_running + 0*num_resumed + 13,107.9                  3.8%
update_after_schedule cost(num_reqs) = 2,924.4*num_reqs + 5,041.7                                                     3.9%
process_outputs       cost(num_outputs) = 2,225.9*num_outputs + 65,341.3   [num_outputs >= 6]                        52-56%
```

**The fixed tax.** `GPUModelRunner._prepare_inputs` costs about 580k
instructions per step whether the batch holds one request or ten (trace
range 560k-633k), against 758 per request. The constant is attributed to
torch dispatch, `__tls_get_addr` 13.2k, `pthread_mutex_lock/unlock` 17.5k,
`_PyArg_ParseStack` 9.1k, `OperatorEntry::lookup` 6.2k: about 35 tiny tensor
ops per step (`copy_to_gpu` at `v1/utils.py:139`, which is a real `copy_` on
this backend, block-table commit at `gpu_model_runner.py:2037`, slices of
positions and sequence lengths, `compute_slot_mapping` at 2255,
`_prepare_input_ids` at 2262). At 64 requests the per-request work is ~55k
and the fixed part ~580k, ten to one. The formula says the batch size is not
what to optimise here; the op count is.

**Third beat for the fixed tax, measured** (`patches/vllm_prepare_inputs.patch`,
`out/vllm_marked_fix`). Temporary nested markers first split the constant
into its sub-steps on a steady ten-request step, then were removed:

```
sub-step                                        before     after
positions/seq_lens to "device"                 105,654    11,101
numpy index prep (repeat, cumsum, gather idx)   85,398    85,419
prev_positions + num_tokens list + mask         79,937    48,093
req_indices/query_pos/num_scheduled H2D         76,610     8,451
compute_slot_mapping                            54,433    53,899
optimistic seq_lens (add + fill_)               44,953    11,647
tail (logits_indices, np.ones)                  36,254    23,158
num_computed_tokens copy                        24,193     5,731
index_select gather                             23,386    23,677
block-table commit                              23,125     4,078
_prepare_input_ids                              22,527     3,474
query_start_loc                                 18,863    15,707
num_accepted_tokens                             10,579     3,740
total                                          665,834   357,660
```

The finding under the finding: `CPUModelRunner._postprocess_tensors` sets
`buffer.gpu = buffer.cpu`, so on this backend every `copy_to_gpu` copies a
tensor onto itself, about 6k instructions of dispatch each, and several
device ops recompute values numpy had already produced. The change makes
`copy_to_gpu` return when the two alias, keeps numpy views of the per-step
buffers, and fills `positions`/`seq_lens`/`logits_indices` from the numpy
values already in hand, guarded so the original device path runs when they
are not aliased. All ten requests' token ids, text, cumulative logprob and
finish reason are byte-identical.

```
prepare_inputs   before  758.2*num_reqs + 106.9*num_tokens + 464,927.7     20.9% irregular
                 after   721.3*num_reqs +  55.2*num_tokens + 205,310.3     26.0%
execute_model    constant 9,224,201 -> 8,968,063; both slopes unchanged to six figures
```

The constant fell 56% and `execute_model`'s constant fell by the same 256k,
which is the composition identity doing its job. At 64 decode requests:
520k to 255k per step. What remains is real work, the numpy index build
(85k over nine calls), the slot-mapping kernel (54k), the gather (23k), and a
20k list comprehension over a Python property that would need an int32
mirror in `_update_states` to remove.

**The step function.** `_update_states` on a steady ten-request step costs
85k; any step in which a request finished costs 205k-265k, and the extra does
not depend on whether one or two finished; each new request adds 70k-90k.
The 55% unexplained share is exactly that: a per-event cost that `derive`
cannot put into a per-count coefficient. The event is `condense()`
(`gpu_input_batch.py:708`) followed by `refresh_metadata()` rebuilding the
sampling metadata with several `copy_slice` ops (840-860, called from
`gpu_model_runner.py:1567`), and per arrival the elementwise assignment
`token_ids_cpu[req_index, :n] = request.prompt_token_ids` (376), 4.5k
instructions of list-to-int32 conversion per prompt. Under continuous
admission at 64 concurrent requests nearly every step pays the ~150k.

**The rebuild.** `_make_cached_request_data` costs 4.9k per running request
per step at 3.8% unexplained, so it is exactly what it looks like:
`get_block_ids` (`kv_cache_manager.py:77-92`) constructs a fresh tuple of
lists and two generator functions per request per step (`PyFunction_New` 242
per request) and the whole `CachedRequestData` (scheduler.py:1525) is rebuilt
from scratch, then walked again in `_update_states`. At 64 requests about
0.33M instructions per step for state that, in steady decode, changed by one
integer per request.

**Third beat for the rebuild, measured** (`patches/vllm_cached_request_data.patch`,
copy `vllm-cpu-rb`, `out/vllm_rb_base` -> `out/vllm_rb_fix`; text, token ids,
cumulative logprob and finish reasons identical for all ten requests):

```
cached_request_data   4,916.2*num_running + 13,027.5    4.2%   ->   1,671*num_running + 15,247.4    3.7%
update_states (consumer)  1,826.5*num_reqs + 27,735*num_new + 11,104*num_finished + 58,905   ->   1,830.8*num_reqs + 27,845*num_new + 11,185*num_finished + 59,088   (unchanged)
```

Fifteen decode steps in sixteen a request gets no new blocks, and the
manager already returns a singleton empty object for that case, so the
scheduler now appends `None` without calling `get_block_ids` at all; the
single-group fast path drops the two generator functions; the five bound
methods and the flags are hoisted out of the loop; and the token list is
stored as the tail the one consumer reads (`gpu_model_runner.py:1527`)
instead of a copy of the whole prompt. Per request the interpreter cost
falls from 2,826 to 1,297. At 64 running requests: 328k to 122k per step.

**Relations** (`out/vllm_marked/learn.txt`, exact at every trigger):

```
cached_request_data.num_running = last(schedule.running)
update_states.num_new      = last(execute_model.num_reqs) - last(schedule.running)
update_states.num_finished = last(prepare_inputs.num_reqs) - last(schedule.running)
schedule.waiting           = cum(generate_loop.unfinished) - cum(update_states.num_new)
```

The last two are worth pausing on: the number of finished requests the model
runner will process is learned as "what the runner prepared last step minus
what the scheduler still has running", and the waiting queue as "everything
submitted minus everything the runner has admitted", both without reading a
line of the scheduler.

---

### vLLM case B. Admitting a request: what a prompt costs before its first token

Eleven regions on the admission and teardown path (`examples/vllm_mark_req.py`),
driver `examples/vllm_run_req.py`: 16 prompts from 12 to 662 tokens, four
output tokens each so admission dominates, and a second `generate()` over the
same prompts to see what is cached. Runs `out/vllm_req` and `out/vllm_req_n`
(instrumented 36.9 s and 46.1 s with late attach).

```
render_prompt        cost(prompt_chars) = 2,089.7*prompt_chars + 281,254.6   [prompt_chars >= 270]   29.6% irregular
process_inputs       cost(num_tokens)   = 315.6*num_tokens + 372,902.8       [num_tokens >= 62]       4.3%
    per-token: PyObject_RichCompareBool 116, PyLong_AsSsize_t 74, PyList_Size 33, PyIter_Next 30
    constant:  _PyEval_EvalFrameDefault 132,612
engine_add_request   cost(num_tokens)   = 544.8*num_tokens + 603,204.4       [num_tokens >= 62]      12.0%
request_init         cost(num_prompt)   = 79.3*num_prompt + 23,844.1                                  58.6%
    irregular: _PyObject_GC_Resize 30,053
core_add_request     cost(num_tokens, num_prompt) = 0*num_tokens + 0*num_prompt + 40,717.4             5.9%
sched_free_request   cost(running, num_blocks, num_tokens) = 0*running + 1,988.3*num_blocks - 13.2*num_tokens + 41,142.4   13.0%
kv_free              cost(num_blocks, num_tokens) = 1,526.9*num_blocks - 8.5*num_tokens + 8,291.4       11.8%
```

**The tokenizer is the per-request cost and nothing caches it.** 2,090
instructions per prompt character, and the second pass over identical
prompts costs the same (9,233,195 then 9,173,733 for the 2,970-character
set). It is 51% of admission on the first pass and 82% on the second. A
2k-token prompt is about 19M instructions, paid again on every call.

**The per-token slope of `process_inputs` is a bounds check.** 315.6 per
token, attributed entirely to `RichCompareBool`, `PyLong_AsSsize_t`,
`PyIter_Next` and `PyList_Size`: that is `max(prompt_ids)` and
`min(prompt_ids)` at `vllm/v1/engine/input_processor.py:485-486`, two full
Python scans of a token list the tokenizer just produced. 646k per 2k-token
request, for nothing.

**373k instructions of fixed work per request, before any token is
touched.** All interpreter, dominated by `SamplingParams.clone()`, which is
`copy.deepcopy` (`vllm/sampling_params.py:769-772`, called from
`input_processor.py:329` with `skip_clone` defaulting to False), plus
validation; `core_add_request` and `sched_add_request` add 45k more, both
flat in everything. 27M instructions of object copying per 64 requests,
independent of prompt size.

**`Request.__init__` has a staircase the declared state cannot fit.** Per-point
means by prompt length: 34.5k at 12 tokens, 39.7k at 122, then 88.0k at
162, 118.1k at 302, 163.3k at 422, 208.2k at 542, 253.3k at 662. Flat within
each 128-token block, about 45k more per block. `num_prompt` fits 79 per
token and leaves 58.6% unexplained; the real driver is `num_prompt // 128`,
the block hashes computed at construction (`update_block_hashes()` at
`vllm/v1/request.py:211`) plus a full copy of the token list (`request.py:146`,
the `_PyObject_GC_Resize` in the residue). A caller reasoning in tokens
cannot see it; a caller who declares blocks gets a formula. 16 blocks of a
2k prompt: ~750k per request.

**The detokenizer decodes the whole prompt at admission.** `engine_add_request`
net of its nested regions is 145k + ~210 per prompt token:
`FastIncrementalDetokenizer.__init__` builds `DecodeStream(ids=prompt_token_ids)`
(`vllm/v1/engine/detokenizer.py:184`) to prime a stream that will only ever
emit the new tokens. ~430k per 2k-token request, discarded.

**The first request pays a disk scan.** The first `process_inputs` trigger
costs 48,027,055 instructions against 406,340 for the same prompt on the
second pass; the whole 99% irregular share of the small-prompt regime is
that one call. It is `_validate_logits_processors` loading plugins through
`importlib.metadata.entry_points()` (`vllm/v1/sample/logits_processor/__init__.py:57`),
reading 170 distributions' metadata, on the admission path rather than at
startup: first-request latency, not model load.

**Third beat, measured** (`patches/vllm_admission.patch`, `out/vllm_req_fix`;
all 32 generated texts and token id lists identical):

```
process_inputs       315.6*num_tokens + 372,902.8   ->   109.2*num_tokens + 386,776.3
engine_add_request   544.8*num_tokens + 603,204.4   ->   227.5*num_tokens + 618,328.6
```

Two changes. The bounds check becomes one C pass, `array("L", prompt_ids)`,
which proves every id is non-negative by succeeding and falls back to the
original two scans, with the original messages, if it does not; the
per-token attribution that read `RichCompareBool`, `PyLong_AsSsize_t`,
`PyList_Size`, `PyIter_Next` now reads `PyInit_array`, `PyLong_AsUnsignedLong`,
`PySequence_GetItem`. And the detokenizer primes its stream with the last
seven prompt tokens instead of all of them, the constant the slow path
already uses; for opt-125m's byte-level decoder this is provably
equivalent, and it was checked against all 50,265 vocabulary ids as the
first output token and 48k random sequences with zero mismatches. That
argument is decoder-specific, and a non-concatenative decoder would need a
guard. Per 2k-token prompt: about 409k fewer instructions in
`process_inputs` (-40%) and 635k in `engine_add_request` (-37%); break-even
at 67 tokens.

The tool also chose between candidates: measured under drperf,
`np.asarray(prompt_ids)` costs 332 per token, worse than the two scans it
would replace, and `all(map(...))` four times worse; only `array("L")` at
110 beat CPython's `max`/`min` at 156 per pass. A fix picked from
intuition would have been a regression.

**Third beat for the staircase, measured** (`patches/vllm_request_init.patch`,
`out/vllm_req_blocks`, `out/vllm_req_fix2`). First the fit: `num_blocks` is
not reachable from the constructor's arguments, so the hasher closure now
publishes its block size and the marker reads it. With that state declared:

```
request_init   cost(num_prompt, num_blocks) = -4.0*num_prompt + 43,273.3*num_blocks + 25,363.4     57.7% -> 12.7% irregular
    per block: _PyObject_GC_Resize 19,526, _PyEval_EvalFrameDefault 3,714, PyLong_AsLongAndOverflow 2,706, PyList_AsTuple 1,635, SHA1_Init 1,240
```

The 79 per token was the staircase seen through the wrong state; per block
it is 43k and per token it is nothing. Then the change: the prompt copy has
to stay (`_all_token_ids` is mutated by the session and connector paths),
but every reader of `block_hashes` runs from `Scheduler.schedule` or later,
so the hashes became a lazy attribute computed on first read. All 32 outputs,
all 54 block hashes and the prefix-cache hit counts are identical.

```
request_init         78.5*n + 23,998 (57.7%)     ->   -2.5*n + 1,086*blocks + 18,829 (34.1%)     662 tokens: 254,024 -> 29,128
engine_add_request   227.5*n + 618,329 (13.6%)   ->   136.8*n + 620,710 (7.0%)                   662 tokens: 1,011,290 -> 760,785
```

About 692k instructions per 2k-token prompt leave the admission path. They
do not leave the program: `schedule` at sixteen waiting rose from 2,655,476
to 3,523,500 per call, and the +2.46M there matches the -2.46M off admission
across the 32 requests exactly. This one moves work to where it is needed
and shortens time-to-first-schedule; it does not reduce total instructions,
and the formulas say so.

**Teardown is per block, and the running list is rebuilt per step.**
`_free_request` is 1,988 per block (of which `kv_free` 1,527) plus 41k, with
`running` at exactly 0: it does not scan the running list. The scan is
`self.running = remove_all(...)` at `scheduler.py:2035`, outside that
region, and surfaces as `update_from_output`'s 4,938 per running request.

**Relations** (`out/vllm_req/learn.txt`, `out/vllm_req_n/learn.txt`):

```
engine_step.unfinished = cum(add_requests_loop.num_prompts) - count(kv_free)
schedule.waiting       = cum(add_requests_loop.num_prompts) - cum(execute_model.num_reqs) + cum(schedule.running)
core_add_request.num_prompt = last(process_inputs.num_tokens) = last(engine_add_request.num_tokens) = last(request_init.num_prompt)
kv_free.num_blocks     = last(sched_free_request.num_blocks)
```

The first says the step loop's load is admitted minus freed, exactly; the
third says five regions bill the same prompt length, so their slopes add:
2,090 per character, then 316, 229 and 79 per token, then 45k per 128-token
block, all for one input.

---

### vLLM case C. The input batch under churn: what an arrival and a departure cost

Driver `examples/vllm_run_batch.py` forces replacement: 24 requests through
`max_num_seqs=8` with output lengths spread 4..40, so most steps see an
arrival or a departure. Markers from `examples/vllm_mark_batch.py`. Runs
`out/vllm_batch` (82 steps, 25 admissions, 23 removals) and `out/vllm_batch_long`
(86-326-token prompts).

```
update_states     cost(num_reqs, num_new, num_finished) = 1,048.2*num_reqs + 45,598.9*num_new + 22,118.6*num_finished + 95,570.1   49.9% irregular
add_request       cost(num_prompt, num_blocks) = 275.2*num_prompt + 0*num_blocks + 46,456.8                                      2.8%
    per-prompt-token: PyArray_DiscoverDTypeAndShape_Recursive 85, PyArray_Pack 69, INT_setitem 58, PyLong_AsLong 22
condense          cost(num_reqs, empty) = 9.6*num_reqs + 12,163*empty + 11,258.2                                                45.1%
refresh_metadata  cost(num_reqs, num_added, num_moved) = 0*num_reqs + 3,420.9*num_added + 4,894.5*num_moved + 32,234.9           36.3%
remove_request    cost(num_reqs) = 37.8*num_reqs + 14,897   [num_reqs >= 4]                                                        0.0%
bt_commit         cost(num_reqs) = 0*num_reqs + 22,005.3                                                                          0.0%
```

**An arrival costs per prompt token, for a copy.** `InputBatch.add_request`
is 275-333 instructions per prompt token at under 3% unexplained, and the
attribution is numpy's scalar path: `PyArray_Pack`, `INT_setitem`,
`PyLong_AsLong`. That is `token_ids_cpu[req_index, :n] = request.prompt_token_ids`
and its two siblings at `gpu_input_batch.py:376/382/387`, a Python list
assigned element by element into an int32 row. A 2k-token prompt is about
615k instructions to admit, more than a whole steady step of the runner.

**A departure costs per row moved, not per token.** `condense` is 2.4k with
nothing to move and 54k-80k per row moved (12,163 per `empty` in the fit,
the rest in its 45% residue). The long run, with rows of 326 tokens instead
of 86, changed nothing: the cost is about 17 separate numpy row assignments
plus `block_table.move_row` (`gpu_input_batch.py:765-786`), each a full
dispatch, not the bytes copied. Then `refresh_metadata` rebuilds all sampling
metadata on any change, 10k when nothing changed and 79k-128k when something
did (`:846/858`). With 64 requests and continuous replacement: ~16k to
remove, ~54k to condense, ~73k to rebuild metadata, per finish, every step
one finishes.

**Third beat, measured** (`patches/vllm_input_batch.patch`, `out/vllm_batch_fix`,
`out/vllm_batch_long_fix`; text and token ids identical for all 24 requests
on both variants, plus a 150-trial differential test of the batch's thirteen
arrays, block tables and sampling metadata against the pristine module):

```
add_request        275.2*num_prompt + 46,457    ->   202.9*num_prompt + 42,629       (long prompts: 332.7 -> 269.6)
refresh_metadata   at the steady replace (8 requests, 1 added): 83,361 -> 44,595 per call   (-46.5%)
condense           per moved row, bursts of >= 3: 47,366 -> 33,844   (-28.5%); single departures unchanged
update_states      1,048.2*num_reqs + 45,598.9*num_new + 22,118.6*num_finished + 95,570  ->  856.2*num_reqs + 43,314.2*num_new + 19,919.1*num_finished + 94,570
```

The arrival copy is the instructive one. Ten candidates were measured under
drperf before choosing (`out/rowfill*`): `np.asarray` 334 per element,
`np.array(dtype=int32)` 334, `torch.tensor` 830, `np.fromiter` 269,
`array("i")` + `frombuffer` 271, every one with a larger constant than the
status quo's 333 + 3.6k. What won on both slope and constant is a cached
`memoryview` of each row assigned from `array("i", ids)`: 271 per element,
3,188 constant. The obvious rewrite would have been a regression, and the
ids arrive as a Python list everywhere upstream, so a cached array would
move the 270 rather than remove it. `refresh_metadata` is memoised on the
tuple of scalars it depends on, since every field is a scalar, a view into
storage that never moves, or a container mutated in place. `condense`
gathers `(src, dst)` pairs and applies each scalar array's moves in one
fancy-index assignment (destinations are always below sources, so nothing
overlaps); the measured crossover is 2.7 rows, so it batches at three.

Per arrival at 64 requests with 2k-token prompts about 168k fewer
instructions (131k in `add_request`, 36.5k in the metadata rebuild); per
burst of eight departures about 72k. Smaller than the surprise suggested,
and the formulas said why before the change: the per-token cost is a
conversion that has no cheaper form for a Python list, and the per-row cost
is dispatch count, which batching can only amortise.

**The steady step is not steady either.** At `num_new = num_finished = 0`
the trace means give `5,714*num_reqs + 79,617` for `update_states` while the
fit says 1,048 per request; the rest sits in the residue, and the attribution
names it: `PyFrozenSet_New`, `_PyDict_Next`, `PySet_Discard`, the set
arithmetic `cached_req_ids - (scheduled_req_ids - resumed_req_ids)` at
`gpu_model_runner.py:1287-1301` and the every-request loop at `:1404`, run
whether or not anything changed. Together with case A's `prepare_inputs`
constant, about a million instructions per step at 64 requests that do not
depend on the tokens being generated, single-threaded, while the OpenMP
workers (excluded from these counts, 0.3M-6.2M of spinning per call) wait.

**Relations** (`out/vllm_batch/learn.txt`, exact at all 82 steps):

```
update_states.num_new       = last(execute_model.num_reqs) - last(schedule.running)
update_states.num_finished  = last(bt_commit.num_reqs) - last(schedule.running)
refresh_metadata.num_added  = last(update_states.num_new)
schedule.waiting            = cum(generate_loop.unfinished) - count(add_request)
schedule.running            = count(add_request) + last(engine_step.unfinished) - cum(generate_loop.unfinished)
```

The scheduler's admission count sets, one for one, how many `add_request`,
`condense` and metadata rebuilds the runner pays, so an admission policy
that admits more per step is priced by these formulas before it is written.

---

### vLLM case D. Sampling with penalties: a per-step cost that grows with everything generated so far

Same prompts, two modes, driver `examples/vllm_run_samp.py` with markers from
`examples/mark_samp.py`: greedy (`out/vllm_samp_greedy`) and penalised
(`temperature 0.7, top_k 40, top_p 0.9, repetition 1.2, frequency 0.5,
presence 0.3`, `out/vllm_samp_pen`). Twelve requests, output lengths 16..96,
672 generated tokens in both.

```
penalised
sample            cost(num_reqs) = 31,190,378.7*num_reqs + 1,029,802.3                                                     7.9% irregular
topk_topp         cost(num_reqs, k, p_flag) = 27,849,583.1*num_reqs + 0*k + 0*p_flag + 471,687                             8.3%
    per-request: std::__introsort_loop 6,851,396, __log1p_fma 6,532,525, at::CPUGeneratorImpl::random64 5,726,822
logitsprocs       cost(num_reqs) = 3,342,904.9*num_reqs + 443,222.2                                                        6.3%
apply_penalties   cost(num_reqs, max_len, total_tokens) = 2,657,744.8*num_reqs + 2.7*max_len + 352.9*total_tokens + 412,343.9   21.0%
pen_tensors       cost(num_reqs, max_len, total_tokens) = 3,299.1*num_reqs - 3*max_len + 309.9*total_tokens + 29,953.4      5.1%
    per-total_tokens: PyArray_Pack 69, PyArray_DiscoverDTypeAndShape_Recursive 64, LONG_setitem 57
greedy
sample            cost(num_reqs) = 740,547.9*num_reqs + 545,467.7   [num_reqs >= 6]                                        0.0%
```

**The quadratic.** `pen_tensors` is the padded tensor of every request's
output token ids, rebuilt every step (`penalties.py:47` into
`torch_utils.py:731`, `padded_x[ind, :len] = blocktb`), and it costs 309.9
instructions per token already generated, in numpy's element-by-element
conversion; `apply_penalties` adds ~43 per token for the `scatter_add_`.
`learn` supplies the proof that this is history and not batch size:

```
apply_penalties.max_len = count(apply_penalties) - 2*count(generate_loop) + 2
```

the padded width is the step index, exactly, at every trigger. So the
per-step cost of penalties is `353 x (tokens generated so far by all
requests)`, which sums to a quadratic over a generation. At 64 requests
generating 1,000 tokens the last step pays 22.6M instructions and the
generation about 1.1 x 10^10, to re-encode a history that changed by 64
tokens. This tensor is built on the host in both backends; only the
vocabulary-sized kernels below are CPU-specific figures.

**Per-request, penalised is 42x greedy.** `sample` is 740k per request per
step greedy and 31.2M penalised. 27.85M of that is `topk_topp`: a full sort
of the 50,272-entry vocabulary (`topk_topp_sampler.py:388`) plus `log1p` and
`random64` exponential noise over the whole vocabulary per request, for a
top-k of 40. On this backend the sampler, not the model, is the step at
scale: ~2 x 10^12 instructions of sampling against 4.7 x 10^10 greedy for
64 x 1,000.

**Third beat, measured** (`patches/vllm_penalties.patch`, `out/vllm_samp_pen_fix`;
token ids and text of all twelve requests byte-identical by SHA-256):

```
pen_tensors       before  3,299.1*num_reqs - 3*max_len + 309.9*total_tokens + 29,953.4     5.1% irregular
                  after     376.8*num_reqs + 0*max_len +   3.0*total_tokens + 29,213.6    66.7%
apply_penalties   before  2,657,744.8*num_reqs + 2.7*max_len + 352.9*total_tokens + 412,343.9
                  after   2,654,584.5*num_reqs + 2.0*max_len +  50.2*total_tokens + 370,733.1
```

One file changed, `penalties.py`: a per-request int64 array cached by the
identity of its output-token list, extended by the newly appended tokens
each step, with the padded matrix filled by row copies. The per-token
column that read `PyArray_Pack`, `DiscoverDTypeAndShape`, `LONG_setitem`,
`PyLong_AsLong` before reads one function after, a strided memcpy at 3.0
per token. The coefficient the second beat pointed at is the one that
moved, by two orders of magnitude, and nothing else did (`sample` is
31.19M then 31.20M per request). On this twelve-request workload the saving
is 0.02% of the loop, invisible in wall time; at 64 x 1,000 the formula
puts the final step at 0.25M instead of 20M and the run at 0.15 G instead
of 10.2 G, and the quadratic term is gone. The 66.7% irregular after the
change is the cache hit/miss branch, now the only thing left in a region
that costs a tenth of what it did.

**A negative result worth having.** The survey expected `_make_sampling_metadata`
to be rebuilt per step; it is called 8 times in 98 steps, only on batch
change, and `max_prompt` carries a negative coefficient in the greedy run.
The per-step metadata cost is `refresh_metadata`'s ~51k constant, not a
rebuild. The measurement corrected the reading of the code.

**Relations** (`out/vllm_samp_pen/learn.txt`): `topk_topp.num_reqs = last(apply_penalties.num_reqs) = last(sample.num_reqs) = last(engine_step.unfinished)`,
`pen_tensors.total_tokens = last(apply_penalties.total_tokens)`, and the
`max_len` identity above, which chain every sampling coefficient to batch
occupancy and step index, so the sampler's cost for any workload is a
calculation rather than a run.

One stock-vLLM issue met on the way, not caused by the markers: with chunked
prefill and per-request seeds the CPU backend crashes in
`gpu_model_runner.py:3826` (`gen.get_offset()`, "CPU Generator does not use
offset"); `max_num_batched_tokens=2048` avoids it.

---

### vLLM case E. The output path: a surprise that was mostly the markers

Driver `examples/vllm_run_out.py` runs the same 370-token workload three ways,
FINAL_ONLY through `LLM.generate` and CUMULATIVE and DELTA through the engine
directly. The first measurement, with seven nested Python regions on the
path (`out/vllm_out`), read:

```
process_outputs      cost(num_outputs, num_active) = 82,643.4*num_outputs + 12,842.8*num_active - 20,711.7   52.9% irregular
completion_output    cost(num_tokens, total, kind) = 0*num_tokens + 0*total + 0*kind + 41,722.2               8.3%
request_output       cost(num_outputs, total, prompt, kind) = 0*... + 10,454.7                                8.2%
```

and the reading was that 63% of the per-request per-step cost was
constructing two dataclasses. **That reading was wrong, and the third beat
is what found out.** Reducing the markers to two, with no code change:

```
out/vllm_out        (7 markers)   process_outputs = 82,643.4*num_outputs + 12,842.8*num_active - 20,711.7    52.9%
out/vllm_out_clean  (2 markers)   process_outputs = 30,153.5*num_outputs + 13,663.7*num_active + 2,952.9     26.2%
```

`num_outputs` equals `num_active` at 191 of 194 points, so only their sum is
identified: 95.5k per request per step became 43.8k by removing markers. A
Python region with even one state costs ~11.4k to construct and drperf's
calibration subtracts 582, so five nested regions per request per step were
most of the number. Marker-free and split by output mode
(`out/vllm_out_po_ph_before_*`), the true per-request per-step cost is
8,248 in FINAL_ONLY, 29,780 CUMULATIVE, 30,703 DELTA, and the FINAL_ONLY gap
proves the objects are not built per step: `make_request_output` already
returns early at `output_processor.py:293-296`. What remains is the
detokenizer (`tokenizers::step_decode_stream`, `malloc`, `realloc`,
`memcpy`) and loop bookkeeping. The 12.8k "charge for being alive" was a
collinearity artifact of the same two states; its functions are per-token
detokenization.

**Third beat, measured** (`patches/vllm_output_path.patch`,
`examples/vllm_verify_out.py`, 752 of 752 output records byte-identical):
skipping the `make_request_output` call in FINAL_ONLY rather than entering
it to return saves 1,258 instructions per request per step, 8,247.5 to
6,989.4 (-15.3%), about 80k per step at 64 requests. The lazy string join
for `output_text +=` was implemented, fuzzed over 6,000 schedules with zero
mismatches, and rejected: it saves 0.046 us per step in FINAL_ONLY and costs
0.322 us in CUMULATIVE, which the original formula predicted, since
`1.8*toks - 0.509*have` nets to about zero once `have` is about `4*toks`.

**What this case is for.** It is the cautionary one: a nested-marker layout
produced a plausible, attributable, wrong surprise, and only the discipline
of re-measuring with fewer markers before optimising caught it. The two
signs were there in the first output, a negative constant and a 53% irregular
share on a region whose work should be regular, and the caveat about marker
construction cost was already written in this document's notes without
being applied to these numbers.

---

### vLLM case F. Prefix caching: what a block hash costs, and a conservation law for resident KV

Driver `examples/vllm_run2_kv.py`: a ~50-token shared prefix, prompts of 60
to 600 tokens, `block_size` 16 so blocks fill during decode, twelve then
twenty-four requests (`out/vllm_kv`, `out/vllm_kv24`; 36 s and 41 s with late
attach). Seven markers from `examples/vllm_mark_kv.py`.

```
kv_cache_full_blocks    cost(num_new, num_cached) = 7,267.2*num_new + 0*num_cached + 4,521.4                          7.1% irregular
    per new block: _PyEval_EvalFrameDefault 3,992, _Py_HashBytes 198, PyBytes_FromString 160, PyLong_AsUnsignedLong 153
kv_get_computed_blocks  cost(num_tokens, num_hashes) = 768.6*num_tokens - 6,161.1*num_hashes + 13,486.4                2.3%
kv_block_hasher         cost(num_hashes, num_tokens) = -16,664*num_hashes + 1,041.1*num_tokens - 6,764.7               15.0%   (degenerate: num_hashes = num_tokens // 16)
kv_allocate_slots       cost(num_new_tokens, num_computed) = 245.4*num_new_tokens + 0.105*num_computed + 15,372.6     66.7%
kv_free                 cost(num_blocks, num_tokens) = 424.2*num_blocks - 12*num_tokens + 7,497.4   (24 requests)     48.1%
kv_common_prefix_blocks cost(num_running, num_blocks) = 0*num_running + 0*num_blocks + 1,750.7                       70.2%
detokenize_update       cost(num_new, text_len) = 0*num_new + 0*text_len + 5,349.1                                   72.5%
```

**A block hash is three copies and two hashes.** Per 16-token block the
hasher costs about 19,700 instructions (730,164 for a 37-block prompt in
the trace). `kv_cache_utils.py:717` slices `request.all_token_ids[i:j]`,
which `ConstantList.__getitem__` (`v1/utils.py:80`) returns as a fresh list;
`:601` copies it into a tuple; `hashing.py:39` pickles it and runs SHA-256.
Then the 32-byte digest is re-hashed by CPython on every probe and insert:
`make_block_hash_with_group_id` (`:67`) allocates a 36-byte key each time,
and `_insert_block_hash` hashes it twice, `contain()` at `block_pool.py:616`
and `insert()` at `:627`. The signature is in the per-new-block column:
`_Py_HashBytes`, `PyBytes_FromString`, `PyLong_AsUnsignedLong`. A 2k-token
prompt is 125 blocks, ~2.5M instructions to hash on admission; probing the
prefix cache costs ~6,900 per block for what is one dictionary lookup.

**The no-op calls cost more than the work.** `request_block_hasher` runs on
every generated token (`Request.append_output_token_ids`); fifteen calls in
sixteen return at `:695` having hashed nothing, at 1,677-1,990 instructions
each. Amortised, the wasted entry cost (~1,594 per token) exceeds the real
hashing (~1,294 per token). `kv_allocate_slots` has the same shape at a
larger scale, ~36,500 instructions per request per step to allocate one
token's worth of slot. Per concurrent request per decode step, hasher plus
allocate plus detokenize come to ~50k of Python before any model work.

**A per-step scan of the shared prefix.** `get_num_common_prefix_blocks`
(`single_type_kv_cache_manager.py:823-830`) runs every step on `running[0]`
and walks its blocks while `ref_cnt == len(self.req_to_blocks)`, evaluating
`len()` inside the loop. Both declared states got coefficient 0 and the
region reads 70% unexplained, because the cost follows neither: the trace
gives ~580 per block scanned, 22,939 at 40 blocks against 3,233 at six. It
scales with the shared prefix in blocks, not with the batch: a 500-token
system prompt is ~21k per scheduler step, at any batch size.

**Third beat for the prefix scan, measured** (`patches/vllm_common_prefix.patch`,
`out/vllm_rb_kvbase` -> `out/vllm_rb_kvfix`; the value returned at every
scheduler step logged and identical, outputs identical):

```
kv_common_prefix_blocks   0*num_running + 0*num_blocks + 1,765.4    70.0%   ->   0*num_running + 0*num_blocks + 2,934.3    8.8%
per call, own thread: 40 blocks 22,800 -> 6,767; 29 blocks 15,121 -> 5,167; 21 blocks 11,360 -> 4,393; 4 blocks 3,279 -> 2,778
```

`len()` is hoisted out of the loop and the result memoised on (request id,
number of running requests, block count, a ref-count epoch bumped at every
mutation that can touch a held block: `touch`, `free_blocks`, the two
copy-on-write sites; `get_new_blocks` only appends, which the block count
already keys). Hit rate 65% on this workload, blocks scanned 400 to 142.
At a 500-token shared prefix about 21k to 3k per step on a hit, at any batch
size. The constant rose because the scan stopped hiding in the residue.

**Relations** (`out/vllm_kv/learn.txt`, `out/vllm_kv24/learn.txt`):

```
attention.kv_tokens = count(detokenize_update) - cum(kv_free.num_tokens) + cum(kv_get_computed_blocks.num_tokens)   (504/504)
kv_free.num_blocks  = last(kv_common_prefix_blocks.num_blocks)                                                       (25/25)
schedule.running    = count(kv_get_computed_blocks) - count(kv_free)
engine_step.unfinished = cum(generate_loop.unfinished) - count(kv_free)
```

The first is the KV cache's conservation law, recovered from counts alone:
what attention has to read is every prompt token admitted, plus one per
detokenised output, minus every token freed. It held at all 504 attention
calls.

**Third beat, measured** (`patches/vllm_kv_hash.patch`, `out/vllm_kv_fix`,
24 requests, identical text, identical 456 block hashes in production
order, identical prefix-cache hits):

```
                                   before                       after
hasher per 16-token block          19,630 + 1,746 per call      19,009 + 2,182   (-3.2%)
no-op per-token hasher calls       530 of 592 triggers          0 of 62; the call is gone
no-op call, native micro           2,327                        1,334            (-993 per call)
kv_cache_full_blocks               7,266*num_new + 4,480        6,839.6*num_new + 4,765.2   (-5.9% per block)
```

Three changes: the hasher's boundary test moved to the caller so the
fifteen no-op calls per block never happen; the `ConstantList` frame per
slice hoisted out of the loop; and `contain()` + `insert()` replaced by one
`setdefault`. The equivalence check needed `PYTHONHASHSEED` pinned, because
`NONE_HASH` is `os.urandom(32)` otherwise. Per decode step at 64 requests the
saving is about 64k instructions; per 2k-token prompt about 134k, 3.9% of the
~3.4M spent hashing and inserting it.

**And a correction the third beat forced.** The "three copies" reading
above was wrong in proportion. A per-step micro-measurement of one block
gives: `ConstantList` slice 1,986 (of which the Python frame 688), the tuple
649, `pickle.dumps` 6,263, `sha256` 4,207, `generate_block_hash_extra_keys`
4,825. The copies are a tenth of the block; the serialisation is the cost,
and it is load-bearing: the tuple is what gets pickled, a list pickles to
different bytes, and the one-copy route through `islice` costs 1.8x more.
What the surprise reduces to is that the hash input is built by the
general-purpose pickler, ~6k for sixteen integers.

**A lesson on declared states.** `num_hashes` is `num_tokens // 16` at every
point, so the two hashing regions fitted a degenerate plane with a negative
`num_hashes` coefficient and a negative constant. A derived state carries
no information the base state lacks and costs a degree of freedom; the
useful second state would have been the one the code branches on, whether
this call crossed a block boundary.

---

## Video generation: Wan 2.1 in diffusers, the host side

The pipeline for the most widely used open video model, `WanPipeline` in
diffusers (source checkout `c5469b7`), built from a tiny randomly
initialised config so a full call runs on CPU in 0.3-5 s: a 2-layer
transformer of 64 hidden, a `AutoencoderKLWan` with base dim 8, the default
flow-match Euler scheduler, precomputed prompt embeddings. 51 runs over a
grid of frames {5, 9, 17} x steps {4, 6, 8} x resolution {128, 192, 256} and
a batch/text grid (`videogen/run_tiny.py`, markers `videogen/mark_wan.py`,
runs `out/videogen_tiny`, `out/videogen_batch`, `out/videogen_sweep`). There
is no GPU here, so the matmul and attention kernels are counted too; they
land almost entirely in the irregular term (`mkl_blas_def_sgemm_kernel`,
`cpu_flash_attention`, `somatcopy`), and the affine coefficients and
constants are the host orchestration. Read those.

```
wan_call            = 4,537,754.2*num_frames + 3,075.2*height + 0*width + 11,431,003.3*steps + 27,397,965.9   98.7% irregular
denoise_step        = 0*batch + 51,290.3*frames + 2,457.9*height + 0*width + 12,257,258.1                      93.0%
transformer_forward = 0*batch + 55,729.1*frames + 27,874.9*seq_len + 6,111,945                                 76.7%
block               = 0*batch + 12,424.7*seq_len + 0*text_len + 2,172,643.1                                    79.5%
attn                = 0*batch + 421.6*seq_len + 0*heads + 448.2*kv_len + 423,543.8                             95.7%
rope                = 29.9*frames + 0*height + 0*width + 312,303.4                                             35.2%
cfg                 = 59,421.1*frames + 268.1*height + 0*width + 437.5*numel + 6,327,426.6                     76.4%
sched_step          = 0*batch + 105.8*frames + 1.1*numel + 63,619.2                                             0.1%
set_timesteps       = 105*steps + 201,993.1                                                                     0.1%
vae_decode_frames   = 0*batch + 8,219,409.3*frames + 9,365.7*height + 447,552.7                                99.7%
cond_embed          = 3,855.4*batch - 37*text_len + 617,350.4                                                  55.9%
```

**Surprise 1: the rotary embedding is recomputed on every forward.**
`WanRotaryPosEmbed.forward` (`transformer_wan.py:395`, called at `:668`)
depends only on `hidden_states.shape`, and runs on every transformer call:
312k fixed instructions plus ~400k irregular per call, twice per step with
CFG. At 81 frames and 480x832 that is 33.5 MB of identical cos and sin
rebuilt 100 times per 50-step call, 3.3 GB of the same tensor.

**Surprise 2: the prompt is re-projected every step.**
`self.text_embedder(encoder_hidden_states)` at `transformer_wan.py:347` runs
on every forward and every CFG branch on an input that does not change
within a call: `cond_embed` is 617k fixed here; for the 1.3B model about
8.9 GFLOP per forward, ~0.9 TFLOP per video, for one projection.

**Surprise 3: the VAE decode rebuilds the video per frame.**
`autoencoder_kl_wan.py:1197-1205` decodes latent frame by latent frame and
does `out = torch.cat([out, out_], 2)` each iteration, so the bytes copied
are quadratic in frames. Measured per latent frame: 568.5M at 2, 666.7M at
3, 735.1M at 5 (+29%), with `somatcopy` the top irregular symbol. At 21
latent frames (81 output frames) the penalty is roughly ten times larger.
`_encode` at `:1154` has the same shape.

**The fixed per-step dispatch.** `denoise_step` 12.26M per step, `block`
2.17M per layer, `attn` 424k per attention, all shape-independent
interpreter and dispatch (`_PyEval_EvalFrameDefault`, `PyDict_Contains`,
`OperatorEntry::lookup`). At 30 layers that is ~91M instructions of host
time per forward before any kernel, 100 forwards per call. Smaller items:
a full-size `torch.ones` mask per call at `pipeline_wan.py:574` used only by
Wan 2.2's `expand_timesteps`, and `hidden_states.contiguous()` per forward
at `:674`.

**The fit beat, owed and now paid** (`videogen/mark_fit.py`, `videogen/wan-fit`
rebuilt from the pristine checkout, `out/videogen_fit`, same 27-point grid).
Declaring the product the attention kernel scales with:

```
attn                 421.6*seq_len + 448.2*kv_len + 423,543.8                          95.7%
                 ->  1,150.4*seq_len + 1,244.3*kv_len + 39.9*sq + 0*batch + 1,986,510.3   37.1%   (sq = seq_len*kv_len)
block                12,424.7*seq_len + 2,172,643.1                                     79.5%
                 ->  27,970.5*seq_len + 40.1*sq + 2,374,257.6                            23.3%
transformer_forward  55,729.1*frames + 27,874.9*seq_len + 6,111,945                      76.7%
                 ->  57,926.8*seq_len + 80.2*sq + 6,513,670.2                            24.6%
```

The square lands where it should: `mkl_blas_def_sgemm_kernel_0_zen` 33.4,
`sgemm_scopy` 5.3, `sgemm_mscale` 1.4 per element of the attention matrix
in `attn` and `block`, and exactly twice that in `transformer_forward`, two
layers. What is left in all three is one thing, `at::native::cpu_flash_attention`
(2.6M + 1.6M per attention call), a fused kernel whose block count is not
affine in `seq_len*kv_len` because of its tiling and tail handling; no
product state reaches it. At production those kernels are GPU work; what
transfers is the constants and the linear host terms: `attn` 1.99M,
`block` 2.37M + 28k per token, `transformer_forward` 6.51M + 58k per token,
`denoise_step` 12.9M, per call.

**A derive bug this exposed.** `wan_call` got worse, 98.7% to 99.7%, and its
`11,431,003*steps` term, the largest host term at production, became
`0*steps` with the note "linear function of the earlier states". It is
not. `lib/derive.py:_solve` marks a column dependent when its pivot falls
below `1e-9 * max|A|`; with `sq` around 6.4e12 in the basis the threshold
is ~6.4e3 while the `steps` column's contribution is 72, so `steps` is
dropped unconditionally, and the same mechanism removed `frames` from
`transformer_forward` and `steps` from `denoise_step`. Declaring a large
computed state next to a small one costs the small one. The fix is to
scale columns before solving; the workaround is to declare the square in
units that keep the magnitudes comparable. Done (`mark_fit2.py`,
`out/videogen_fit2`, `sq_k = seq_len*kv_len // 1024`, `area_k = h*w // 64`):

```
wan_call       0*steps + 2,197,527*frames + 0.14*sq + 10*area + 8,750,015                    99.7%
           ->  11,838,056.2*steps + 4,712,994*frames + 614.7*sq_k + 797.5*area_k + 29,880,238.2   98.7%
transformer_forward  ... + 0*frames + 6,513,670   ->   61,041.4*seq_len + 79,726.8*sq_k + 55,843.9*frames + 6,747,196.1   23.4%
attn per-sq_k attribution: sgemm_kernel 34,232.1, sgemm_scopy 5,390.1, sgemm_mscale 1,407.6  (33.43, 5.26, 1.37 per element: unchanged)
```

`steps` is back at 11.84M per step against 11.43M in the unsquared
baseline, attributed to `_PyEval_EvalFrameDefault` 1.24M and
`PyDict_Contains` 400k, host dispatch as claimed; `frames` is back in
`transformer_forward` at 55.8k against 55.7k. Replaying `_solve`'s pivot
test on the state points reproduces every drop in `videogen_fit` and none
in `videogen_fit2`.


**Relations** (exact at every trigger): `attn.seq_len = last(block.seq_len) = last(transformer_forward.seq_len)`,
`rope.{frames,height,width} = last(denoise_step.*)`, `vae_decode.frames = last(denoise_step.frames)`,
`count(vae_decode_chunk) = cum(vae_decode.frames)` (one decoder pass per latent frame),
`set_timesteps.steps = last(wan_call.steps)`.

**Third beat, measured** (`videogen/patches/wan_{rope,text_embed,vae_cat,misc}.patch`,
`out/videogen_fix`, `out/videogen_fix_batch`; latents and decoded video
byte-identical by SHA-256 at five grid points, VAE encode and decode
separately identical at 1, 5, 9, 17 frames):

```
rope         cost(frames, height, width) = 29.9*frames + 0*height + 0*width + 312,303.4   35.2%   ->   0.5*frames + 44,711.8    22.9%
             mean per call 482,987 -> 58,612 (-87.9%); first call 782k, every cached call 13,679
cond_embed   cost(batch, text_len) = 3,855.4*batch - 37*text_len + 617,350.4   55.9%   ->   3,943*batch + 0.07*text_len + 513,647.5   34.2%
             mean per call 780,728 -> 564,337 (-27.7%); the residue is the timestep embedding, which does change per step
wan_call     4,537,754*num_frames + 11,431,003*steps + 27,397,966   ->   4,501,651*num_frames + 10,750,513*steps + 27,537,440
```

The rotary cache keys on (frames, height, width, device, dtype) and is
invalidated on shape change; the prompt projection is memoised on tensor
identity and version, bypassed under autograd, at most four entries. At
81 frames, 480x832, 50 steps with CFG on the 1.3B model these are about
0.72 s and 1.92 s of host time per call on this machine, and both also
remove GPU work: two 32,760 x 128 tables per forward, and ~870 GFLOP of
projection per video.

**And a correction the third beat forced.** The rising per-latent-frame
VAE cost was not the `torch.cat`. Per latent frame at 256 wide, baseline /
cat fix only / all fixes: 573.5M / 560.8M / 560.6M at 2 frames, 666.6M /
661.4M / 657.9M at 3, 738.0M / 737.7M / 735.0M at 5. It still rises,
because chunk 0 (`first_chunk=True`) emits one output frame at ~265M
while every later chunk emits four at ~855M, and `(265 + (F-1)*855)/F`
reproduces 562, 662 and 741M exactly. The cat is real but ~1% at this
tiny VAE (base dim 8 against 96 in production), where a chunk does about
1/144 of the convolution work per output pixel. At production width the
list-then-cat measures 927.5 ms to 92.3 ms for the concatenation itself
(4.12 GB of copies to 388 MB), so the fix stands, on different evidence
than the surprise cited. `.contiguous()` at `transformer_wan.py:674` is
not a no-op either: after `flatten(2).transpose(1, 2)` the strides are
`(81920, 1, 1280)`, so a guard would save nothing, and none was applied.


---

### Wan case B. The paths the first pass did not mark: rotary application, callbacks, the VAE posterior, tiling

24 more regions (`videogen/mark_more.py`, copy `videogen/wan-more`), seven grids
of 90 points in all (`out/videogen_more_*`), driver `videogen/run_more.py`
with modes for text-to-video, VAE encode, tiled decode, and a real tiny
`UMT5EncoderModel` so prompt encoding is measured too.

```
attn_rope      = 5,764.3*seq_len + 0*heads + 0*batch + 320,506.1        0.4% irregular
    per token: c10::function_ref callback 3,064, serial_for_each 1,264, callback 896, DimCounter::increment 352
attn_qkv       = 1,622.5*seq_len + 3,023.2*kv_len + 0*heads + 405,870.8  1.4%
attn_sdpa      = 157*seq_len + 1.9*kv_len + 0*heads + 97,709.3          98.6%
attn_out       = 1,403.2*seq_len + 0*heads + 0*batch + 129,319.2         0.0%
callback_step  = 14,019.5*ninputs + 0.00755*numel + 10,872.6             5.4%
    per name: PyDict_Contains 2,436, PyDict_SetItem 2,044, PyDict_Update 1,850, PyObject_SetItem 1,469
dgd_init       = 0*chans + 14.2*numel + 114,569.1                        2.7%   (mkl_vml_sExp 13.6 of the 14.2)
blend_v_r      = 114,147.7*extent + 64.4*frames + 0*width + 4,934        5.3%
blend_h_r      = 112,494.6*extent + 64.4*frames + 0*height + 5,068.2    15.4%
pp_stack       = 0*batch - 8*frames + 0*height + 26,205.5               94.5%
prompt_clean_r = 10,931.8*batch + 439.7*chars + 101,552.5               93.7%
```

**Rotary application is the most expensive host phase of attention.**
`apply_rotary_emb` (`transformer_wan.py:104-118`) costs 5,764 per token at
0.4% unexplained, 3.6x the QKV projections and 4.1x the output projection,
and not one of its top functions is arithmetic: the stride-2 interleaved
layout puts TensorIterator on its scalar `DimCounter` path, with two
full-size temporaries and two strided copies, 45 instructions per rotated
element. The tables it reads are half duplicates: `get_1d_rotary_pos_embed`
with `repeat_interleave_real=True` emits two 16.8 MB tables at production of
which `apply_rotary_emb` uses `cos[..., 0::2]` and `sin[..., 1::2]` only
(`even == odd` verified).

**`locals()` per callback name per step.** `pipeline_wan.py:640` builds the
callback's inputs by calling `locals()` for each requested name, 14,019
instructions of dictionary machinery per name; the default is three names,
42k per step to read three variables already in scope.

**The VAE posterior computes what it discards.** `DiagonalGaussianDistribution.__init__`
(`vae.py:693-694`) evaluates `std` and `var` eagerly, an `exp` over the whole
latent, 14.2 per element with `mkl_vml_sExp` 13.6 of it; `mode()`, which is
what the pipeline uses, reads neither. 9.3 ms per encode at production.

**The blend loops, and why not to fix them.** `blend_v`/`blend_h`
(`autoencoder_kl_wan.py:1268-1281`) cost 114k per row regardless of the row's
size, pure descriptor and bound-method allocation, 161M per tiled decode at
production. The formula also says the vectorised form would lose: at 81
frames a row holds 62k elements, Python is ~27% of it, and the one-shot
version allocates a 15.9 MB temporary and measures slower (21.9 to 27.4 ms).
It dominates only for tiny tiles.

**Two negatives worth having.** `pp_stack` is the one serial pass over the
whole video (0.35-0.48 per element, single-threaded, ~34M on one core at
production) and is what `pt_to_numpy`'s deferred transpose lands on;
`prompt_clean`'s residue (ftfy) is content-dependent and genuinely
undeclarable, with 68 instructions per character in `_PyErr_CheckSignals`
from its codec probing.

**Third beat, measured** (`videogen/patches/wan_more_{rope_apply,dgd_lazy,cb_locals}.patch`,
`out/videogen_fix2_*`; latents, video, 55 digests of rotary outputs,
posterior statistics, tiled configs and post-processing all identical):

```
dgd_init        14.2*numel + 114,569.1      2.7%   ->   0.349*numel + 70,030      1.8%     (40x on the slope; 9.31 -> 0.10 ms per production encode)
callback_step   14,019.5*ninputs + 10,872.6 5.4%   ->   425*ninputs + 26,940      0.0%     (33x per name)
attn_rope       5,764.3*seq_len + 320,506   0.4%   ->   5,675.3*seq_len + 323,964 0.4%     (-1.5% instructions; 210.9 -> 157.7 ms per q or k at production, -25% wall)
```

The rotary line is the honest caveat of this whole document in one row:
the fix removes memory traffic and temporaries, not instructions, so the
instruction cost function reports -1.5% where the clock reports -25%.
Instructions are not time, and this is the place it mattered.

The client key-merge bug bit again: the pre-existing one-state
`set_timesteps(steps=2)` merged into `encode_prompt(batch=2)`; every new
region here carries a constant tag state to keep signatures unique.

---

### vLLM case G. The scheduler under pressure: what waiting costs, what preemption costs, and a correction

Three workloads on a copy marked at the scheduler's queue and admission paths
(`examples/vllm_mark_sched.py`, `examples/vllm_run_sched.py`): saturation
(48 requests through `max_num_seqs=8`, up to 43 waiting, `out/vllm_sched_sat`),
priority scheduling under KV pressure (20 requests, 44 blocks of 16 tokens,
prefix caching off, 15 preemptions, `out/vllm_sched_prio`), and chunked
prefill (six 990-1,590-token prompts through a 128-token budget,
`out/vllm_sched_chunk`). A fourth run with finer sub-regions was discarded:
1,980 unmatched region ends, the late-attach race.

```
sat    schedule              cost(running, waiting) = 971.3*running + 0*waiting + 69,719.8                  94.1% irregular
       sched_waiting_eval    cost(num_tokens, num_computed, waiting) = 0 + 0 + 0 + 187,660.7               15.4%
       cached_request_data   cost(num_running, ...) = 4,852*num_running + 12,743.2                          1.8%
       fcfs_peek / fcfs_pop  2,572.6 / 441, flat in queue length                                             0.0%
prio   sched_preempt         cost(running, preempted, num_new_tokens) = 2,140.5*running + 0 + 0 + 94,086.3   14.9%
           per running: _PyTuple_Resize 358.6, PyTuple_GetSlice 210.6, PyObject_RichCompareBool 203.8, PyTuple_New 139.4
       prio_pop 76*queue_len + 3,057 | prio_prepend 32.3*queue_len + 19,746 | prio_peek 270
chunk  kv_allocate_slots     cost(num_new_tokens, num_computed, num_new_computed, num_tokens) = 8.4*num_new_tokens - 0.1*num_computed + 12.2*num_new_computed + 0 + 27,253.2   49.0%
```

**The correction.** Case B reported `schedule` at 55,206 and the baseline at
60,134 per waiting request per step. With 43 requests genuinely waiting the
coefficient is 0: `scheduler.py:762` breaks out before any per-waiting work
once `max_num_seqs` is reached, and `learn` shows `count(sched_waiting_eval)
= count(fcfs_peek) = count(fcfs_pop) = count(kv_get_computed_blocks)` = 49 in
139 steps, one probe per admission and none otherwise. The earlier
coefficient was admission cost aliased onto a `waiting` state that moved in
step with admissions in those runs. Two hundred waiting requests cost the
scheduler nothing per step, in that regime.

**The regime where they do cost.** When admission is blocked by KV memory
instead of by `max_num_seqs` (the priority run), the head of the queue is
evaluated every step: 168 `sched_waiting_eval` for 36 admissions, 132 wasted
evaluations at ~203k each, re-running `get_computed_blocks`
(`kv_cache_manager.py:250`) and `allocate_slots` from scratch. Nothing is
cached across steps; with prefix caching on, the probe alone is 17.5k rather
than 1.2k. That is ~200k per step for as long as the pool stays full.

**Preemption is five linear scans per victim.** 2,140 per running request,
attributed to tuple construction and comparison: `max(self.running, key=...)`
at `scheduler.py:648` builds a fresh 2-tuple per running request, then
`self.running.index()` at 654, `del` at 655, `in scheduled_running_reqs` at
662 and `.remove()` at 664. Every preemption in this run entered with
`preempted=0`, so the multi-victim `while True` loop, which would be
O(running²) per step, was not exercised and is not bounded here.

**Chunked prefill is a flat tax per chunk.** `kv_allocate_slots` costs ~63k
per 127-token chunk against 37.9k per decode token, flat in `num_computed`
(69 to 831) and in prompt length; the prefix probe and the waiting
evaluation run once per request, not per chunk. So a 2k-token prompt pays
about 1.0M in `allocate_slots` over its 16 chunks, ~492 per token, from
chunk count alone.

**Relations** (exact at every trigger):

```
sat    schedule.waiting = count(fcfs_add) - count(fcfs_peek)
       schedule.running = count(fcfs_peek) - cum(sched_remove_all.n_remove)
       update_after_schedule.num_tokens = cum(kv_allocate_slots.num_new_tokens) - cum(execute_model.num_tokens)
prio   count(prio_prepend) = count(sched_preempt) = count(sched_preempt_request)
       schedule.running = count(prio_pop) - count(prio_prepend) - cum(sched_remove_all.n_remove)
```

The second priority relation is the preemption conservation law, running
equals admissions minus preemptions minus finishes, learned from counts.

**Third beat, measured** (`patches/vllm_sched_head.patch`,
`patches/vllm_sched_preempt.patch`, copy `vllm-cpu-schedfix`,
`out/vllm_schedfix_prio`, `out/vllm_schedfix_sat`). Equivalence is stronger
than output text here: a scheduler hook logged, per step, the running queue
in admission order, the preempted ids, the scheduled token counts and the
number of queue peeks, and the logs are byte-identical before and after on
all three workloads, so the control flow is unchanged, not just the result.

```
sched_preempt       2,140.5*running + 94,086.3    14.9%   ->   422.8*running + 98,683.2    9.9%
sched_waiting_eval  triggers 168 -> 59 (36 admissions + 23 forced by real frees); total 23,714,077 -> 10,319,210 (-56.5%)
schedule (prio)     847.6*running + 115*waiting + 22,207    ->   655.5*running + 102.2*waiting + 26,293
schedule (sat)      971.3*running + 0*waiting + 69,720      ->   891.4*running + 0*waiting + 70,841     (unchanged, as expected: no waste there)
```

The memo keys on the request's identity and progress, the free-block count
(an allocation cannot turn a refusal into an admission, only a free can) and
a new generation counter on the prefix-cache map, and is guarded off for
connectors, LoRA, Mamba and speculative paths; 109 of the 132 wasted
evaluations disappear at 122,888 each. The preemption becomes one pass
carrying `(priority, arrival_time)` as scalars with the same first-maximal
tie-break as `max`, and one `del`. At 64 running with the pool full: about
123k per step saved by the memo, plus ~110k per preemption.

**What the residues name.** `schedule` at 94-98% unexplained is the
admission and preemption events themselves, which happen on 35% of steps
independently of `running` and `waiting`; the states that would explain it
are `admitted` and `preempted` on `schedule`. `kv_allocate_slots` at 49%
in the chunked run is the 25k step from one to 127 new tokens landing in
irregular blocks; the state is `ceil(num_new_tokens / block_size)`.

At 64 running and 200 waiting with 2k prompts the affine scheduler tax is
about 2.9M instructions per step, the waiting requests add nothing, and the
two costs that do scale are the ones above: ~200k per step while the pool
is full, and ~1.0M per prompt admitted in chunks.

---

### Wan case C. The per-step host constant, decomposed: cross-attention re-projects the prompt 3,000 times

`denoise_step` carries a ~11.5M-13M constant per step that no declared state
touches. Fifty-five temporary probes (`videogen/mark_tax_probe.py`, one state
each, unique multiplier bands so the client cannot merge them, verified over
27 runs x 76 regions with exact trigger counts) split it into its sub-steps,
then were removed. The step scaffolding is 1.3% of it; the rest is the two
transformer calls, and inside those, per layer:

```
sub-step (per layer)     before       after            sub-step (per forward)   before     after
bl_attn1 (self-attn)   1,129,822   1,059,251           tf_cond (timestep+text)   632,627   416,146
bl_attn2 (cross-attn)  1,013,395     763,454           tf_shift (modulation)      51,627    41,824
   ax_qkv                378,712     137,932           tf_rope                   104,682   105,452
bl_ffn                   214,604     221,311           tf_patch                  115,045   114,522
bl_norm1/3               212,394     192,827           at_rope (per self-attn)   320,122   279,012
bl_norm2                  78,346      60,556           at_out                    118,046    87,985
bl_mod (6-way chunk)      49,040      40,774           tf_normout                110,746    99,314
```

Attribution throughout is `_PyEval_EvalFrameDefault`, `PyDict_Contains`,
`_PyObject_GenericGetAttrWithDict` (the `nn.Module.__getattr__` walk),
`_int_malloc/_int_free`, `at::native::slice` in the modulation chunk, and
in `ax_qkv` alone `mkl_blas_def_sgemm_kernel_0_zen` 130,563 of 378,712.

**The surprise.** Cross-attention's `to_k` and `to_v` project
`encoder_hidden_states`, which is fixed for the whole call, on every block
of every forward: 30 layers x 100 forwards = 3,000 projections per video
where 60 (one per layer per CFG branch) would do. The rest of the list is
the same shape at smaller scale: the timestep embedding and the
`scale_shift_table + temb` modulation are recomputed for the second CFG
branch although the pipeline passes it the same `timestep` tensor;
`FP32LayerNorm` re-upcasts an input and weights that are already fp32;
`to_out[1]` is `Dropout(p=0)`, a module call and an ATen dispatch for the
identity; the two rotary half-tables are sliced twice per attention and
`out.type_as` after `empty_like` is always the identity.

**Third beat, measured** (`videogen/patches/wan_tax.patch`, `out/videogen_tax`;
latents and video identical at all five equivalence points, e.g. latents
`c64589693a19156c…`, video `5167edcaa39e7205…`), all memoised on tensor
identity plus `_version`, bypassed under autograd, or provably identity:

```
ax_qkv (cross-attn K/V)   378,712 -> 137,932   (-63.6%)
tf_cond                   632,627 -> 416,146   (-34.2%)
bl_norm2                   78,346 ->  60,556   (-22.7%)
at_out                    118,046 ->  87,985   (-25.5%)
bl_mod / tf_shift          49,040 ->  40,774 / 51,627 -> 41,824
at_rope                   320,122 -> 279,012   (-12.8%)
block                12,424.5*seq_len + 2,177,148.7   ->   12,424*seq_len + 1,967,858.2
transformer_forward  54,619.5*frames + 27,605*seq_len + 5,678,082   ->   54,911*frames + 27,604.2*seq_len + 5,005,886.4
wan_call             ... + 10,750,513.4*steps + 27,537,440   ->   ... + 9,502,853.1*steps + 27,488,895
```

At production (81 frames, 480x832, 50 steps, CFG, 30 layers): 209k fewer
host instructions per layer call x 3,000, 254k per forward x 100, about 653M
per video, the constant tax from 6.67 G to 6.02 G (-9.8%). The part that
matters is not the host: the K/V memo removes 2,940 of 3,000 cross-attention
projections, 14.2 TFLOP per video, for 189 MB of bf16 residency. A
per-block constant that no state explained, attributed partly to an sgemm
kernel, was the tell.

---

### vLLM case H. n-gram speculative decoding on the CPU backend: the cost function says it cannot pay, and it does not

Marked copy `vllm-cpu-spec/`, `mark_spec.py` (two marker sets, `spec` and
`stop`), driver `examples/vllm_run_spec.py`. Two things had to be fixed before
any of it measured what it claimed to:

- **`--late` attached inside `LLM(...)`.** `NgramProposer.__init__` calls
  `propose()` to prime the numba JIT, so with the `spec` set the first marker of
  the run fires during the model build: DynamoRIO attached there, the rest of the
  load ran instrumented (3m31s instead of 51s), and the JIT of the KMP kernel
  landed inside `ngram_scan` as a single 6,064,741,919-instruction trigger, taking
  `ngram_propose` to 99.9% irregular. The driver now replaces `perfmark.region`
  with a null context manager for the duration of `LLM(...)` **and the warm-up
  generate**, and restores it at `vllm_attach`. Anyone marking a lazily-JIT-ed or
  lazily-initialised path needs the same trick.
- **Every new region carries a constant `tag` state.** The client's fast key
  cache compares region and state-name strings by pointer, so two regions sharing
  a root, a state count and identical state values merge (see the notes below).
  `sample(num_reqs=8)` and `engine_step(unfinished=8)` are exactly that pair in
  steady-state decode, as are `update_from_output(8,0,0)` and
  `update_states(8,0,0)` once `num_draft` is declared. Tags 9001..9018 make the
  value tuples unique. All runs below print zero "perfmark_end without matching
  begin".

```
export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-spec:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
export VLLM_CPU_OMP_THREADS_BIND=all OMP_NUM_THREADS=8
python mark_spec.py vllm-cpu-spec spec          # or: ... stop
/home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \
    --max-slots 2097152 -o out/vllm_spec_k3 \
    -- <venv>/python examples/vllm_run_spec.py mode=spec reqs=8 k=3
```

Eight requests, `facebook/opt-125m`, staggered `max_tokens` 64..22 so the batch
drains one request at a time; half the prompts repeat a phrase, half do not.
Runs: `out/vllm_spec_k3`, `_k5`, `_plain` (control), `_long` (~640-token
prompts), `_mix`/`_mix5` (`pfam=1`, random-number prompts so the lookup misses).

```
ngram_scan         cost(num_valid, ctx, k, tag) = 9,926.9*num_valid + 18*ctx + 0*k + 24,536.1        6.6% irregular
                       per ctx: 25.1 <no module> (the numba KMP kernel)
ngram_propose      cost(num_reqs, k, ctx, tag) = 7,717.2*num_reqs + 0*k + 6.6*ctx + 213,274.3       13.6%
ngram_gather       cost(num_reqs, num_valid, tag) = 1,961*num_reqs + 3,086.7*num_valid + 240.3       2.1%
                       per num_reqs: 423.1 _PyEval_EvalFrameDefault, 338.3 PyObject_RichCompareBool
reject_sample      cost(num_reqs, num_draft, max_spec, tag) = 1,107,763.8*num_reqs + 1,127,991.2*num_draft + 412,557.4   8.0%
                       per num_draft: 703,812.6 + 402,204.6 c10::function_ref<...>::callback
sample             cost(num_reqs, tag) = 704,436*num_reqs + 91,492.9                                17.7%
                       per num_reqs: 703,897.2 c10::function_ref<...>::callback
execute_model      cost(num_tokens, num_reqs) = 117,149,875.2*num_tokens + 2,449,800.1*num_reqs + 1,116,215,516.6   2.4%
update_from_output cost(running, num_draft, num_accepted, tag) = 24,722.9*running + 3,104.8*num_draft + 0*num_accepted + 43,589.8   25.0%
update_states      cost(num_reqs, num_new, num_draft, tag) = -3,418.9*num_reqs + 139,104.7*num_new + 2,625.1*num_draft + 98,271.3  19.6%
prepare_inputs     cost(num_reqs, num_tokens, num_draft, tag) = 42,167.6*num_reqs - 416.4*num_tokens - 11,516.5*num_draft + 794,596.8  1.1%
```

**Speculation cannot pay here, and the forward's cost function says so before
you run it.** `execute_model` measured per call: 1,455,869,529 for 8 scored
tokens (plain), 5,654,179,627 for 32 (K=3), 8,455,452,379 for 48 (K=5) — that
is 182.0M, 176.7M and 176.2M instructions **per scored token**. The CPU forward
has a 3.2% economy of scale between 8 and 48 tokens per step, and none beyond.
An n-gram draft of K tokens scores K+1 to emit at most K+1, so the whole upside
is that 3.2%. On the debit side `reject_sample` charges 1,127,991 per draft
token where `sample` charges 704,436 per row, so sampling per output token goes
704k to 1,136k, +61%. Measured, same 344 tokens: plain 70.5 tok/s, K=3 73.2,
K=5 73.2; total instructions `generate_loop` 24.322 G (plain), 24.791 G (K=3),
24.143 G (K=5). A wash, exactly as the two coefficients predict. This is a GPU
optimisation ported to a backend whose arithmetic does not support it, and the
formula is the cheapest possible way to see that.

**The proposer rescans the entire context every step.** Fitting `ngram_scan`'s
own-thread cost across all six runs (num_valid 1..8, ctx 250..6,431):

```
ngram_scan self = 9,822*num_valid + 22.9*ctx + 33,258     max residual 1.1%
```

`ctx` is the sum of the context lengths of the requests scanned, so this is 23
instructions per token of history, per step, forever. The KMP loop in
`_find_longest_matched_ngram_and_propose_tokens`
(`ngram_proposer.py:263-296`) walks `origin_tokens[::-1]` from index 1 to
`total_token` every call; its answer depends only on the last `max_ngram`
tokens and on where they previously occurred, both of which an incremental
index would carry across steps. `learn` states it as a conservation law:
`ngram_scan.ctx = cumend(ngram_scan.ctx) - 296`, exact at 17/17 triggers.

**`ngram_gather` is quadratic in the batch.** `if i in valid_ngram_requests`
(`ngram_proposer.py:131`) is a list membership test inside a loop over all
requests. Fitting the per-call cost at num_reqs = num_valid = n:

```
quadratic  69.6*n^2 + 4,577*n + 1,553     max residual   61  (0.15%)
linear                5,197*n +   522     max residual  526  (1.2%)
```

`PyObject_RichCompareBool` at 338.3 per request is the scan. At n = 64 the
quadratic term is 285k of 580k instructions per step. `valid_ngram_requests` is
built as a sorted list of indices; a `set`, or zipping the loop against it,
removes the term.

**Acceptance.** With repetitive prompts and greedy decoding on a 125M model
every draft is accepted, and `learn` says so exactly:
`update_from_output.num_accepted = last(prepare_inputs.num_draft)` at 17/17
triggers in `out/vllm_spec_k3`. With random-number prompts (`pfam=1`,
`out/vllm_spec_mix`) the relation breaks and least squares gives
`num_accepted ~ 0.726*last(prepare_inputs.num_draft)` (R^2 0.999). `ngram_scan`
costs the same either way: the scan runs for every request that has a sampled
token, whether or not it will produce a usable draft. That decoupling — the
cost proportional to context, the benefit proportional to acceptance — is what
the two formulas make explicit.

At 64 requests with 1,000-token contexts and K=5, per step: `ngram_scan`
2.13M, `ngram_gather` 0.55M, `reject_sample` 1,107,764*64 + 1,127,991*320 =
432M, against a forward of 176M * 384 = 67.6G. The proposer is noise; the
rejection sampler is 0.6%; the forward is everything, and it is 6x what the
same 64 tokens would have cost without speculation unless acceptance is near
perfect.

**Third beat for the scan, measured** (`patches/vllm_ngram_index.patch`,
`out/vllm_spec_fix_*`, `out/bench_ngram_prod`). Reading the kernel first
mattered: KMP over the reversed context with `>=` updates selects the
*earliest* earlier occurrence of the longest matching suffix, not the most
recent, and a first-occurrence table never changes in an append-only
history, so it reproduces the rule exactly. Per (request, n-gram length) an
open-addressed table of first occurrences, confirmed against the tokens, is
extended by the newly appended tokens each step; a pure-Python index was
tried and rejected at 63.7k per request per step. Equivalence: 32,711
proposals identical across the stock kernel, a brute-force oracle and the
index over 1,500 randomised histories, and byte-identical draft logs and
outputs on all four spec workloads.

```
ngram_scan   before  9,856*num_valid + 22.9*ctx + 32,441   (1.4%)
             after   11,909*num_valid + 0.9*ctx + 34,705   (3.3%), plus a build of ~300 per token indexed, once per request
ngram_gather the 56.4*n^2 term is gone (`set` instead of a list scan)
64 requests x 1,000 tokens, K=5, measured side by side:  ngram_scan 2,125,389 -> 881,113 per step; gather 436,236 -> 221,638
```

A 1.46M per-step saving against a 19.4M one-time build breaks even after
16 steps, so the short driver runs are a wash to worse and the win is
steady-state decode; against the 67.6 G forward per step it remains noise,
which is what case H said the cost function implied before any of this was
built.

### vLLM case H2. Stop strings are free, `min_tokens` is free, and one request's `logprobs=5` bills the whole batch

Second marker set (`python mark_spec.py vllm-cpu-spec stop`), driver modes
`stop` (stop strings on all eight requests, `logprobs=5` on half,
`min_tokens=8` on two, `max_tokens` 128 staggered) and `splain` (control).
`out/vllm_stop`, `out/vllm_splain`, `out/vllm_stop_long` (`max_tokens=384`).

```
check_stop        cost(have, new_chars, nstop, tag) = 0*have + 0*new_chars + 0*nstop + 4,196.8    0.0% irregular
detok_update      cost(num_new, have, toks, tag) = 0*num_new + 0*have + 5.1*toks + 28,113.8      53.8%
logprobs_update   cost(num_logprobs, num_new, have, tag) = 0*... + 289,681.3                     72.7%
gather_logprobs   cost(num_reqs, num_logprobs, tag) = 1,009,495.2*num_reqs + 115,043.4           57.2%
                      per num_reqs: 913,749.3 at::native::AVX2::topk_impl_loop, 88,004 kernel._omp_fn.0
min_tokens_apply  cost(num_reqs, num_affected, tag) = 0*num_reqs + 16,785.7*num_affected + 174    0.0%
logit_bias_apply  cost(num_reqs, num_affected, tag) = 0*num_reqs + 0*num_affected + 138.7         0.0%
sample            cost(num_reqs, tag) = 707,856*num_reqs + 151,166                               79.7%
```

**The stop-string quadratic is gone in 0.28.** `check_stop` is 4,196.8
instructions per call with `0*have` at **0.0% irregular**, and the same
4,211.4 at `max_tokens=384` where `output_text` reaches ~1,900 characters.
`check_stop_strings` starts its `str.find` at `1 - new_char_count -
len(stop_str)` (`detokenizer.py:340`), so it only ever searches the new tail.
The earlier note in this document pointing at a suffix-slice quadratic around
`detokenizer.py:161` should be read as applying to `get_next_output_text`,
which in `FINAL_ONLY` runs once per request, not per step.

**What does grow is `detok_update`, at 5.1 instructions per output token so
far** — the same coefficient at 128 and at 384 output tokens, attributed
entirely to `_PyEval_EvalFrameDefault`, i.e. `self.output_text += ...`
(`detokenizer.py:120`) rebuilding the string each token. 5,100 per step per
request at 1,000 tokens, 2.55M over the request's life. Real, and small.

**`min_tokens` and `logit_bias` cost nothing when unused**: 174 and 138.7
instructions flat, 0.0% irregular, and 16,785.7 per *affected* request when
`min_tokens` is live. No reason to gate them out.

**One request's `logprobs` bills every row.**
`InputBatch.max_num_logprobs` is `max(self.num_logprobs.values())`
(`gpu_input_batch.py:1150-1151`), so `Sampler.forward` runs `log_softmax` and
`torch.topk` over the whole `[num_reqs, 50272]` matrix as soon as one request
sets `logprobs=k`. `learn` states it exactly:

```
gather_logprobs.num_reqs = last(engine_step.unfinished)   exact at 118/118 triggers
```

with only four of the eight requests asking. Natively, half a batch costs the
same as a whole one: `mode=stop max_tokens=128`, 744 tokens, `lp=0` 105.1 tok/s,
`lp=1` (half) 86.1, `lp=2` (all) 85.9.

**The optimise beat.** `patches/vllm_stop.patch`
(`patches/apply_logprobs_rows.py <tree>` applies it; base sources in
`patches/base_stop/`): `InputBatch` publishes the row indices that asked, and
`Sampler` runs the top-k on those rows and scatters the result back into a
full-height tensor. The rows nobody asked about are left at zero and are never
read — `Scheduler.update_from_output` slices `logprobs` per request only when
`sampling_params.num_logprobs is not None` (`scheduler.py:1988-1994`).

```
                       before (out/vllm_stop)                after (out/vllm_stop_after)
gather_logprobs states num_reqs = 2,3,4,5,6,7,8              num_reqs = 1,2,3,4
steady-state row       total/call     64,131,276             59,409,231     -7.4%
  of which other-thr   16,205,197                            11,489,509    -29.1%
  of which own-thr     47,926,078 (OpenMP pool spin)         47,919,723      0.0%
sample self (whole run)   186,894,327                       218,877,207    +17.1%
```

The per-row top-k is ~1.18M instructions and it lives entirely on the OpenMP
worker threads (own-thread cost is flat at 1.29-1.32M per call for one row or
seven); halving the rows removes exactly four of them,
16.21M -> 11.49M = 6.8M + 1.18M*rows. The `sample` increase is the added
`logprobs[rows]` gather and the three `index_copy_` scatters, 250k per call.

Outputs are byte-identical: token ids, text, finish and stop reason,
cumulative logprob and the full top-5 logprob dicts with decoded tokens and
ranks, dumped with `SPEC_DUMP=` and compared —
`lp=0/1/2` and `mode=spec` all match (`sha256 54d35feb5988...` for `lp=1`
before and after).

**And the beat does not move the clock.** Alternating before/after, three
pairs: 85.3/85.7, 84.0/85.9, 85.9/85.8 tok/s. There are eight OpenMP threads
and four rows removed, so the top-k finishes in the same wall time with half
the work. The formula bought a 29% reduction in the region's instruction count
and a correct statement of when it would matter — at 64 requests with 8 asking
it is 56 * 1.18M = 66M instructions per step — but nothing measurable at this
batch size. That is the honest shape of this fix, and it is a shape a
wall-clock profiler cannot express at all: the profiler would have shown the
top-k at 1.2% of wall and stopped.

**Where the time actually is.** Summing the trace, `execute_model` is 96.4% of
`generate_loop` in the plain run, 97.0% with K=3, and 87.1% in the logprobs
run. Every host-side region marked in cases G and H together is inside the
remaining 3%. That is the finding that should govern what gets optimised next
on this backend, and it took one `derive` to establish.

---

### Wan case D. The text encoder's cost follows the padding, quadratically, and the prompt is free

`WanPipeline._get_t5_prompt_embeds` tokenises with `padding="max_length"` at
`max_sequence_length` (512) and runs the UMT5 encoder on the padded batch,
then slices each row to its real length and zero-pads again. Copy
`videogen/wan-t5`, markers `videogen/mark_t5.py`, driver `videogen/run_t5.py`
(encode-prompt only), grid real tokens {8, 32, 128, 480} x max length
{64, 128, 256, 512} x batch {1, 2}, one thread, every point repeated.

**Fit.** With `rtok` (summed real lengths), `ptok` (padded tokens),
`sq = batch*max_len^2/64` and `lsq = max_len^2/64`, on the points where the
prompt is shorter than the budget:

```
t5_enc      -1.2*rtok + 24,402.1*ptok + 20,723.2*sq + 4,625,186                       68.6% irregular   (three states)
t5_enc      24,980*ptok + 46,060.5*sq + 27,714.6*lsq + 6,807,980                      17.7%             (with lsq)
    ptok: mkl sgemm_kernel 10,497, mkl_vml sTanh 7,232        (projections, FFN)
    sq:   mkl sgemm_pst 17,664                                (attention, per padded token pair)
    lsq:  index_select_out_cpu 4,608, mkl_vml sLn 3,320       (the relative-position bias, rebuilt as (1, heads, L, L) in every layer)
```

The real prompt's coefficient is -1.2: it is free. Everything is paid per
padded token and per padded pair, and there is an unbatched L² term because
UMT5 materialises the position bias per layer. A second regime exists: a
prompt that exactly fills the budget is ~35% cheaper, since an all-ones
mask lets transformers skip the (B, 1, L, L) mask tensor.

**Surprise at production.** UMT5-XXL (24 layers, d_model 4096): 2,422 GMAC
per prompt padded to 512 against 148 at 32 real tokens, 4.84 versus 0.30
TFLOP, 16.3x (21.8x for 24 tokens), each layer materialising a 33.6 MB score
tensor and a 67.1 MB position bias where 0.13 and 0.26 MB would do.
Downstream the cross-attention's `kv_len` is exactly `max_sequence_length`:
`attn_qkv = 1,358*seq_len + 2,494.7*kv_len + 369,881` at 0.8% unexplained,
so 3,000 cross-attentions per video run over 512 keys, 154.6 TMAC, where
32 keys would be 9.7.

**Third beat, measured** (`videogen/patches/wan_t5_shortpad.patch`): encode
at the longest real length rounded up to a multiple of 8 (floor 16), then
zero-pad to `max_sequence_length` as before.

```
t5_embeds   25,688.3*ptok + 46,070.5*sq + 27,692*lsq + 6,565,689   ->   693.5*ptok + 34.8*sq - 27.7*lsq + 6,694,193
per call, batch 1, max_len 512:  8 real tokens 384.8M -> 8.07M (47.7x); 32 -> 8.46M (45.5x); 128 -> 17.3M (22.2x); 480 -> 124.5M (3.1x)
```

Prompt embeddings, negative embeddings, latents and decoded video are
bit-identical to pristine diffusers at ten encode points and three full
pipeline calls, worst absolute difference 0.0. The reason is checkable:
T5's position bias is relative and masked scores are shifted by
`finfo.min`, so real-token outputs do not depend on padding, and in float64
lengths 16 to 512 agree with length 8 to 1.55e-15 (a floor of 8 gives
4e-6 because BLAS switches kernel below M = 16).

**The half that cannot be done, and what it says.** Shortening `kv_len`
into the transformer is not behaviour-preserving: cross-attention is
called with `attention_mask=None` (`transformer_wan.py:569`), `to_k` and
`to_v` have biases, and `text_embedder(0)` is not zero, so every one of the
480 pad rows is a real key and removing them moves the output by 0.27 on
a scale of 2.3. The model was trained attending to its own padding;
15/16 of its cross-attention work is spent on it, and that cost is part of
the model now, not of the pipeline.

---

## The fit pass: pushing the above-20% regions down

Every region reported above 20% whose residue named a state was
re-declared and re-measured, in fresh copies (`vllm-cpu-sched-fit`,
`vllm-cpu-out-fit`, `videogen/wan-fitpp`; scripts `examples/vllm_mark_schedfit.py`,
`mark_out_fit.py`, `videogen/mark_fitpp.py`; runs `out/vllm_schedfit5_*`,
`out/vllm_outfit_*`, `videogen/out/videogen_fitpp_*`).

| region | before % | after % | states added |
|---|---|---|---|
| Wan `tiled_encode_r` | 100.0 | 0.1 | `tiles`, `area_frames` (plus a stride-aligned grid and `frames=1`, the second code path) |
| Wan `tiled_decode_r` | 100.0 | 0.4 | `tiles`, `area_frames` |
| Wan `pp_denorm` | 96.0 | 0.0 | `pixels_k` |
| Wan `prompt_clean_r` | 93.7 | 3.8 | `chars`, `nonascii` |
| Wan `postprocess_frames` | 90.7 | 0.1 | `pixels_k` |
| vLLM `detok_update` | 53.0 | 0.0 | `is_first`, `have_k` |
| Wan `attn_rope` (heads grid) | 40.9 | 0.0 | `sh = seq_len*heads`, `head_dim` |
| vLLM `kv_allocate_slots` (chunked / saturated) | 49.0 / 21.3 | 18.2 / 1.4 | `new_blocks`, `is_prefill` |
| vLLM `update_from_output` (chunked / saturated) | 47.5 / 56.7 | 12.4 / 34.8 | `num_reqs`, `num_prefill`, `num_finish` |
| Wan `postprocess_video` | 88.0 | 16.2 | `pixels_k` (the rest is nested `pp_stack`) |
| vLLM `process_outputs` | 26.2 | 25.1 | `num_finished` |
| vLLM `schedule` (saturated) | 94.1 | 85.1 | `admit_cap`, `tight`; its sub-regions fit at 1.2-16.5% |
| Wan `pp_stack` | 94.5 | 95.7 | `pixels_k` (a derive artefact, below) |

**The VAE and the whole call** (`videogen/mark_fitvae.py`, `videogen/wan-fitvae`,
`out/videogen_fitvae_{t2v,enc,dec}` against identical before-grids):

```
wan_call          4,480,269*num_frames + 2,347*height + 0*width + 12,023,646*steps + 27,308,499      98.7%
              ->  1,257,956.1*steps + 121,593.3*sseq + 122,720.4*ssq_k + 23,313,781.2*pix_k + 47,730,295.2   11.5%
vae_decode_chunk  9,155.6*height + 0*width - 4,988,638*first + 18,604,091                          99.3%
              ->  0*tag - 40,182,458.5*first + 156,690.6*area_k + 22,966,099.2*area_frames_k + 104,306,303.6    4.3%
attn_sdpa         157*seq_len + 1.8*kv_len + 0*heads + 95,963                                      98.7%
              ->  157*seq_len + 3.7*kv_len + 33,302.2*sq_k + 0*heads + 108,819                     47.6%   (15.2% on one flash-attention band)
```

| region | before | after | states |
|---|---|---|---|
| `vae_decode_chunk` / `vae_frame_loop` | 99.3 / 99.4 | 4.3 / 4.3 | `first`, `area_k`, `area_frames_k` |
| `vae_decode_frames` / `vae_stage` | 99.7 / 99.7 | 7.4 / 7.4 | `chunks`, `area_k`, `area_frames_k` |
| `vae_encode` / `vae_encode_chunk` | 99.2 / 97.2 | 2.1 / 2.0 | as above |
| `wan_call` | 98.7 | 11.5 | `steps`, `sseq`, `ssq_k`, `pix_k` |
| `denoise_step` / `cfg` | 92.9 / 76.7 | 23.8 / 23.8, 5.2 / 5.0 on one band | `steps`, `frames`, `area_frames_k`, `sq_k` |
| `attn_sdpa` | 98.7 | 47.6, 15.2 on one band | `seq_len`, `kv_len`, `sq_k`, `heads` |

`pix_k` carries the VAE decode and post-processing (`somatcopy2_n` 7.9M and
`sgemm` 4.5M per 1,024 output pixels), `ssq_k` the attention matmuls
(122,723 per unit, four attentions per step at ~30 per element), `sseq` the
projections. What resists is one thing and it is the user's segmented
function made literal: `cpu_flash_attention` is three template
instantiations, `<32,512>`, `<64,512>` and `<256,512>`, chosen by thresholds
on the query length (128 -> 32; 192..720 -> 64; 768 and up -> 256), so the
set of executing blocks changes with size and no entry-time integer is
affine across the bands. Restricting the grid to one band takes
`denoise_step`, `cfg` and `attn_sdpa` to 5.2, 5.0 and 15.2%, the last being
that instantiation's own `ceil(seq/64)` tail. The four-state limit also
bit here: `wan_call` had to drop `chunks`, and because interpreter blocks
are shared between the step loop and the VAE chunk loop, its `steps`
coefficient fell to 1.26M; the per-step host constant is `denoise_step`'s,
13.9M.

Three things the pass found along the way. `tiles` alone left the tiled
regions at 98%: the loop `range(0, h, stride)` clips the last tile, so a
mixed grid spans several tile geometries and only a stride-aligned grid
fits. `detok_update`'s whole residue was the first token of each request,
78k-89k of decode-stream setup (`tokenizers::FlatMap`, `malloc`), so the
state was a flag, not a size. And ftfy's `fix_text` costs 12,420
instructions per character whatever the encoding: the `nonascii`
coefficient is -299, three orders below `chars`.

Three things it could not do. `schedule` contains five code paths, so no
plane fits its blocks although `drperf fit` on the trace explains it at
R² 0.993 (`320,682*count(kv_allocate_slots) - 174,366*running + 292,070`);
the remedy was to fit the sub-regions, which is where the surprises were
anyway. `process_outputs` stays at 25% because the first-token detokenizer
cost and the output kind would need six states and perfmark keys four. And
`pp_stack` is two `__memcpy_avx_unaligned_erms` blocks that alternate
depending on where numpy's destination lands relative to the source: each
carries exactly 1,151.9 per `pixels_k` when it runs and 0 otherwise, their
sum is affine to 0.03% at all ten points, and per-block classification
calls both irregular.

## The Wan fixes on a real GPU: no wall-clock change, and why that is the honest answer

Everything above was measured on CPU, where drperf can count instructions.
The fixes were then run end to end on an NVIDIA A100-SXM4-80GB (GCP box,
`videogen/gpu/run_wan_gpu.py`), with the real Wan2.1-T2V-1.3B weights in
bfloat16, one variant per process, same seed, warm-up outside the timing.

| tree | 33 frames, 12 steps | 81 frames, 30 steps | peak GB | latents digest |
|---|---|---|---|---|
| pristine | 11.549 s | 98.831 s | 14.16 / 15.04 | `ed369696…` / `e92edc7a…` |
| fixes without the T5 change | 11.504 s | 98.897 s | same | identical to pristine |
| all fixes | 11.501 s | 98.992 s | same | `96f0399b…` / `cadd63b6…` |

**No speedup, at either shape.** 0.4% at the small one and nothing at the
large one, inside run-to-run noise. The reason is arithmetic that was
available before the run: the largest fix, memoising the cross-attention
K and V of a fixed prompt, removes 2,940 of 3,000 projections, and at
512 text tokens by 1,536 channels that is about 14.1 TFLOP per video,
which an A100 at roughly 150 TFLOP/s of bfloat16 executes in about
0.1 second out of 99. The rest of the fixes are host-side, and on this
backend the host is not the bottleneck: the same Python that costs 6.7
billion instructions per video is overlapped with kernels that take far
longer.

**What this does and does not invalidate.** The measurements stand: the
work removed is real, verified bit-identical, and would matter wherever
the host is the constraint (CPU inference, a much smaller model, a much
faster accelerator, or many concurrent pipelines sharing one host). What
it invalidates is any suggestion that these particular numbers translate
into A100 wall-clock. drperf's first caveat says instructions are not
time; this is that caveat arriving in the other direction, and it is why
the earlier sections state instruction counts and FLOPs rather than
seconds.

**One fix is not bit-identical in bfloat16.** Everything except the T5
padding change reproduces the pristine digest exactly at both shapes, at
`ed369696…` and `e92edc7a…`. Encoding the prompt at its real length
instead of 512 changes the digest, although on CPU in float32 it was
bit-identical to 0.0 and provably padding-independent through the mask
and the relative position bias. The cause is the reduction order: a
different sequence length selects different kernels and tile shapes, so
bfloat16 rounding differs. That makes it a numerically-equivalent change,
not an exact one, and on this evidence it should be presented that way.

## The vLLM fixes on a real GPU: a gate first, then the regimes where the host is on the critical path

The Wan result above says what the missing step in the loop was: after
"fit, surprise, optimise" there has to be a check that the accelerator
ever waits for the host cost that was just removed. This section applies
that check to the vLLM fixes of cases A to H2 on the same A100.

**Setup.** vLLM 0.28.0 from PyPI (torch 2.13.0+cu130) in
`/home/ava/disk3/vllm/venv` on the GCP box. `base/vllm` is the wheel's
package copied out; `fixed/vllm` is the same copy with 15 files replaced
(`changed_files.txt`). Those 15 files carry every host-side fix from the
vLLM cases, ported from the marked CPU trees by `tools/unmark.py`, which
removes the `with perfmark.region(...)` wrappers and re-indents, so that
each fix is a clean diff against the pristine source: the scheduler-side
rebuild (A), the `copy_to_gpu` short-circuit (A, guarded on the host
device so it is a no-op here), the admission bounds check, detokenizer
priming and lazy block hashes (B), the input batch fill, condense and
sampling-metadata reuse (C), the penalties token cache (D), the
output-path early returns (E), the block hash `insert_if_absent`, the
no-op hasher skip and the common-prefix memo (F), the head-of-queue
admission memo and the single-pass preemption (G), and the n-gram
first-occurrence index (H). The `logprobs` rows fix of H2 is left out:
it touches the same sampling metadata the C fix caches, and the
benchmark does not request logprobs. The wheel's copies of the 15 files
are byte-identical to the CPU tree they were fixed against (`md5sum -c
base_md5.txt`).

**Equivalence.** On the CPU backend, one process, the combined tree
reproduces the base tree exactly: `gpu/vllm_equiv.py` runs 64 prompts
of 8 to 407 words twice (the second pass hits the prefix cache) under
greedy, penalties and `logprobs=3`, and both trees give digest
`d9edb05d23332351` over 5,390 generated tokens
(`out/vllm_equiv_cpu.jsonl`). On the GPU the same digest is not a valid
test: two repeats of the *same* tree differ (`f85e6624…` then
`68fa5407…` for base), because request arrival from the frontend process
changes the batch composition and with it the bfloat16 reduction order,
so greedy ties flip. With the engine in the same process
(`VLLM_ENABLE_V1_MULTIPROCESSING=0`) the batches are deterministic and
the test is valid again: on the A100 with Qwen2.5-0.5B-Instruct, base run
twice and fixed run once give the same four digests, `16d07861f66b`
(greedy), `8fa202e86a1e` (seeded sampling), `10fc2cef7e44` (penalties)
and `b28923defe7e` (`logprobs=3`), over 5,632 tokens
(`out/vllm_equiv_gpu.jsonl`). The combined fix is bit-identical on both
backends.

**The gate, measured.** `nvidia-smi dmon -s u` sampled at 1 Hz during the
runs (`out/vllm_gpu_dmon.log`, windows cut at the run starts in
`out/vllm_gpu_matrix.log`). Samples with the GPU busy, by SM utilisation:

| run | at 100% | 50 to 89% | 1 to 49% |
|---|---|---|---|
| 7B decode, async on, base / fixed | 53 / 54 | 1 / 1 | 38 / 14 (load and warm-up) |
| 7B decode, async off, base / fixed | 2 / 3 | 65 / 65 | 17 / 10 |
| 0.5B decode, async on, base / fixed | 1 / 3 | 2 / 2 | 26 / 27 |
| 0.5B decode, async off, base / fixed | 1 / 2 | 0 / 0 | 35 / 30 |

With async scheduling the 7B timed phase is at 100% in every sample: the
GPU never waits for the host, so no host-side fix can move the wall clock
there, and the first row of the results table is the prediction, not a
disappointment. With async scheduling off the same phase sits at 50 to
89%: the GPU idles while the host schedules, and host work is on the
critical path. On the 0.5B model the GPU is below 50% busy throughout,
whichever way the scheduler runs: that run is host-bound.

**Runs.** `gpu/vllm_bench_gpu.py`, one process per run, `max_num_seqs`
256, `max_model_len` 4096, prefix caching on, greedy, `ignore_eos`, a
64-prompt warm-up outside the timing, best of two timed calls (the second
call hits the prefix cache for every prompt, so "best" is the
prefill-free decode figure). `decode`: 1,024 prompts of 60 to 120
tokens, 256 output tokens each, 262,144 output tokens per call.
`async=-1` is vLLM's default (async scheduling on), `async=0` turns it
off.

| model | workload | async | base | fixed | change |
|---|---|---|---|---|---|
| Qwen2.5-7B-Instruct | decode | on (default) | 22.524 s, 11,639 tok/s | 22.694 s, 11,551 tok/s | -0.7% (noise; GPU at 100% SM) |
| Qwen2.5-7B-Instruct | decode | off | 29.782 s, 8,802 tok/s | 29.229 s, 8,969 tok/s | +1.9% |
| Qwen2.5-0.5B-Instruct | decode | on (default) | 10.254 s, 25,565 tok/s | 9.832 s, 26,662 tok/s | +4.3% |
| Qwen2.5-0.5B-Instruct | decode | off | 12.395 s, 21,149 tok/s | 11.971 s, 21,898 tok/s | +3.5% |
| Qwen2.5-7B-Instruct | decode, repetition and frequency penalties | on | (base run died mid-way; rerun below) | 23.242 s, 11,279 tok/s | |
| Qwen2.5-7B-Instruct | prefill (512 prompts of ~1,000 tokens, 16 out) | on | 2.433 s, 176,343 tok/s total | 2.451 s, 175,105 tok/s | -0.7% (noise) |
| Qwen2.5-7B-Instruct | mixed (512 prompts of 130 to 1,000 tokens, 128 out) | on | 7.360 s, 8,905 tok/s | 7.407 s, 8,848 tok/s | -0.6% (noise) |

**Reading the table.** Every 7B row with async scheduling on is flat, as
the gate says it must be: decode, prefill and mixed all run with the GPU
saturated, and the host work the fixes remove was never on the clock.
Turning async scheduling off costs the 7B decode run 7.3 s: that is the
host work the overlap hides, about 25% of the step at this batch, and
with the host serialised the fixes give back 0.55 s of it. On the 0.5B
model the forward is short enough that the host is on the critical path
even with the overlap, and the same fixes give +4.3% (async on) and
+3.5% (async off).
So the rule the Wan run suggested holds in both directions: the
drperf-found cost turns into wall-clock exactly in proportion to how
much of it the accelerator waits for, and that proportion is a one-line
measurement (`dmon`, or async on versus off) that belongs in the loop
before the optimise beat.

**Second pass, alternated.** The rows that moved were re-run in the
order base, fixed, fixed, base with three timed calls each
(`out/vllm_gpu_results_pass2.jsonl`): 0.5B async on 10.089 s vs 9.901 s
(+1.9%), 0.5B async off 12.188 s vs 11.940 s (+2.1%), 7B async off
29.928 s vs 29.326 s (+2.1%). The gain is real and repeatable but small,
two to four percent where the host is on the critical path and nothing
where it is not; the host profile of the 0.5B step (queued as pass 3 on
the box, `gpu/vllm_hostprof.py`) is the list of what the next drperf
iteration should mark.

## A pure-CPU system: the Kimi Code CLI's cold start, halved

The GPU sections above end on a gate: a host-side fix pays only where the
accelerator waits for the host. A CLI startup has no accelerator, so every
instruction drperf attributes is on the wall clock, and the loop closes
without a caveat. The target is `kimi-cli` 1.50.0 from PyPI, the Kimi Code
CLI, a Python coding agent. Nothing here touches a network: the run ends
at "LLM not set", so the whole measurement is local startup work.

```
python3 -m venv kimi-venv && ./kimi-venv/bin/pip install kimi-cli   # 1.50.0
export PYTHONPATH=/home/ubuntu/drperf-cases/kimi-mark:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
/home/ubuntu/drperf/bin/drperf-dev run --blocks -q --threads 1 --repeat 2 \
    --max-slots 4194304 --state n_tools=1,2,3,4,5,7,8,9,11,13,14,15,16,17 \
    -o out/kimi_fit2 -- ./kimi-venv/bin/python startup/run_kimi.py
```

`startup/run_kimi.py` generates an agent spec holding the first `n_tools`
of the seventeen default tools and runs `kimi --quiet -p hi` in-process
against a fresh `KIMI_HOME`. The package is copied to `kimi-mark/` and put
first on `PYTHONPATH`; `startup/mark.py` inserts the regions, so the marked
tree is reproducible from the pristine one.

**Beat one, the fit.** The obvious state for tool loading is how many tools
there are. drperf refuses it. `derive out/kimi_fit --region load_tools`
splits the range in two and the upper half does not fit:

```
cost(n_tools) = 40,976,735.8*n_tools + 67,426,198.8   [n_tools <= 7]    8.8% irregular
cost(n_tools) =  7,127,579.0*n_tools + 161,553,133.7  [n_tools >= 9]   89.6% irregular
```

89.6% irregular is the tool saying the cost is not a function of the count.
Adding the import-closure size as a second state made it worse (99.9%),
and the raw per-point sums say why: from one tool to seven the region grows
87.1M to 382.9M while `sys.modules` grows by five entries, then the eighth
tool alone adds 1,103M and the fourteenth adds 1,942M. The cost is not
affine in anything, because it is a step function of *which* tools are in
the list. The per-call region says it exactly (`out/kimi_probe`, 17 tools):

| tool | modules it adds | instructions |
|---|---|---|
| `tools.file:ReadFile` (idx 7) | 511 | 1,100,526,152 |
| `tools.web:SearchWeb` (idx 13) | 163 | 1,936,996,159 |
| the other fifteen | 0 to 5 each | 34.5M to 87.1M each |

**Beat two, the surprise.** Two of seventeen tools are 80% of tool loading,
and the reason is a module import each of them triggers.

- `kimi_cli/tools/file/read_media.py:7` reads
  `from kosong.chat_provider.kimi import Kimi`, used once, at line 121, for
  an `isinstance` test. That import is the **OpenAI SDK, 495 modules**. It
  is on the startup path because `tools/file/__init__.py` imports every
  sibling, so asking for `ReadFile` pays for it.
- `kimi_cli/tools/web/fetch.py:5` reads `import trafilatura`, called once,
  at line 102, inside the tool body. That import is an **HTML extraction
  stack: `trafilatura`, `lxml`, `dateparser`, `courlan`, `justext`,
  `htmldate`, `tld`, `pytz`, 166 modules**.
- With those gone, `deferred_import` became the largest region at 3.84G of
  5.68G, and inside it `kimi_cli/soul/toolset.py:30` reads
  `from kosong.tooling.mcp import convert_mcp_content`, called once, at line
  1065, when an MCP tool returns content. That import is the **whole Model
  Context Protocol package, about 300 modules of pydantic models**, loaded
  whether or not any MCP server is configured.
- What was left was not an import. `kosong/tooling/__init__.py:30` validates
  every tool's parameter schema at construction with
  `jsonschema.validate(self.parameters, Draft202012Validator.META_SCHEMA)`.
  The convenience call re-checks the meta-schema against its own meta-schema
  on each of the sixteen calls; building the validator once takes the same
  sixteen validations from 88ms to 9ms.

Each of the four is one line moved or reused. None changes what the program
computes: the imports happen on first use, the validator is the same
validator.

**Beat three, the fix, measured both ways.** Instructions from drperf with
identical markers on both trees (`out/kimi_before2`, `out/kimi_after3`);
wall clock from nine fresh processes per tree (`startup/bench.py`).

| region | before | after | change |
|---|---|---|---|
| process total | 8,655,375,049 | 4,064,157,769 | -53.0% |
| `cli_run` | 7,981,039,387 | 3,541,961,150 | -55.6% |
| `deferred_import` | 3,840,262,560 | 2,758,304,318 | -28.2% |
| `app_create` | 3,963,574,710 | 604,566,911 | -84.7% |
| `load_tools` | 3,773,522,741 | 415,268,876 | -89.0% |
| `boot_import` | 69,988,404 | 69,975,975 | 0.0% |

| cold start, 9 processes | best | median |
|---|---|---|
| stock 1.50.0 | 2.055 s | 2.083 s |
| four fixes | 0.916 s | 0.923 s |

**-53.0% instructions, -55.7% wall clock.** The two agree to 2.7 points,
which is the whole point of a pure-CPU target: here drperf's instruction
count *is* the time, with no gate in between. Startup goes from 2.08s to
0.92s, a 2.3x speedup, from four one-line edits that a profiler would have
shown as "import machinery" and drperf attributed to the four call sites
that cause it.

**Equivalence.** `startup/equiv.py` builds every tool from the default
agent spec on both trees and digests the names and JSON parameter schemas:
`55c7f09cb96db3f8` on both. `startup/functest.py` then exercises the four
changed call sites: `trafilatura.extract` on a fixture returns the same
markdown, `convert_mcp_content` on a text block returns the same part, the
`Kimi` provider class still resolves, and a malformed parameter schema is
still rejected by the now-cached validator. Both trees print the same
record. The four edits are collected in `kimi_fixes.patch`.

**Why this case exists.** The three GPU sections above measure real work
removed that the wall clock did not show, because an A100 was waiting on
something else. This one measures the same kind of work removed on a
machine where nothing else is waiting, and the wall clock moves by exactly
the amount the instruction count predicted. Both halves are needed: the
formula tells you what the work is and where it comes from, and the gate
tells you whether removing it will be visible.

## The same CLI, running: a per-step cost function and a 21% faster session

The cold-start case above is honest about its own weakness. A startup is a
single event with no state to vary, the fit failed twice before the case
turned into a list of two names, and `python -X importtime` would have found
the same four imports. This section is the case that startup could not be:
a region whose cost is a *function* of something the caller varies, where
the surprise is a coefficient rather than a hot function, and where the same
formula, re-derived after the fix, is the verification.

**Driving a real agent loop with no model.** `startup/run_agent_kimi.py`
runs one user turn through the production path with provider type `kimi`
pointed at `startup/stub_llm.py`, an in-process HTTP server on localhost
that replays a fixed script of assistant messages. Every step calls a tool,
each on a different file, because the toolset deduplicates identical calls
and re-reading one path would not grow the conversation. So the session is a
real multi-step agent loop, entirely local, with the history growing by a
controlled amount per step.

The provider type matters. The first attempt used the built-in
`_scripted_echo` provider and measured nothing, because
`_compute_completion_overrides` returns early when the provider is not
Kimi-backed, and the region under study never ran. That is worth stating
plainly: a driver that does not enter the code path produces a clean,
confident zero.

**Beat one, the fit.** The region is `estimate_request_tokens`, which
`KimiSoul` calls once per step, before every model call, over the whole
conversation and every tool schema. Declared states: the number of messages,
the total characters of text in them, and the number of tools.

```
$ drperf run --blocks --repeat 2 --state n_msgs=8,24,40,56,64 \
      --state chars_per_msg=200,800,1600 --state n_tools=5,11,17 \
      -o out/tok_fit2 -- ./kimi-venv/bin/python startup/run_tokens.py steps=3

cost(n_msgs, n_chars, n_tools) = 7,894.7*n_msgs + 437.5*n_chars
                               + 270,272.8*n_tools + 1,967,904.9
    blocks: 2102 affine, 1237 constant, 34 irregular    (0.1% of cost)
```

**0.1% irregular**, three separated coefficients. Getting there took one
correction that drperf asked for: the first sweep held the tool count at
seventeen, and the tool said so rather than guessing, reporting that
`n_tools` was collinear with the other states and folding it into the
constant. Varying it separated the term.

**Beat two, the surprise: two coefficients that should not exist.**

- **437.5 instructions per character of conversation, per step.** Counting
  characters costs one Python loop iteration each, because
  `_estimate_text_tokens` is `sum(char.isascii() for char in text)`: a
  generator frame and an attribute call per character. The cost is per step
  and proportional to the whole history, so over a session it is quadratic.
- **270,272.8 instructions per tool, per step.** Each tool's schema is
  re-serialised with `json.dumps` and re-counted on every step, though the
  toolset hands back the same `Tool` objects for the life of the session.

Neither is visible as a hot function. A profiler reports time inside
`_estimate_text_tokens`; what it does not report is that the time is
proportional to conversation length and paid again on every step, which is
the part that decides whether to fix it and what the fix is worth.

**Beat three, the fix.** Two edits in `kimi_cli/llm.py`, plus a memo for the
per-step message conversion in `kosong/chat_provider/kimi.py`, where
`_convert_message` deep-copies every message in the history on every step.

```python
def _estimate_text_tokens(text: str) -> int:
    if text.isascii():                       # one C scan, the common case
        return (len(text) + 3) // 4
    ascii_count = len(text.encode("ascii", "ignore"))   # exact, still in C
    non_ascii_count = len(text) - ascii_count
    return (ascii_count + 3) // 4 + non_ascii_count
```

**The same formula, re-derived after the fix**, same command, same states:

| term | before | after | factor |
|---|---|---|---|
| per character of history | 437.5 | 0.371 | 1,179x |
| per tool | 270,272.8 | 16,101.2 | 16.8x |
| per message | 7,894.7 | 3,936.7 | 2.0x |
| constant | 1,967,904.9 | 77,810.9 | 25.3x |
| irregular | 0.1% | 1.3% | |

**Regions, over a 40-step session** (`out/tok_before`, `out/tok_after`):

| region | calls | before | after | change |
|---|---|---|---|---|
| `estimate_request_tokens` | 40 | 1,675,521,657 | 22,552,296 | -98.7% |
| of it, `est_history` | 40 | 792,062,423 | 11,771,864 | -98.5% |
| of it, `est_tools` | 40 | 605,830,263 | 2,604,227 | -99.6% |
| of it, `est_system` | 40 | 275,144,162 | 5,644,108 | -97.9% |
| `step_llm_call` | 40 | 6,126,634,942 | 5,670,573,716 | -7.4% |
| `step_injections` | 52 | 2,128,670,715 | 1,868,104,744 | -12.2% |
| `agent_step` | 40 | 8,085,458,030 | 5,978,360,180 | -26.1% |
| whole process | | 17,399,606,671 | 11,894,112,319 | -31.6% |

**End to end**, fresh processes, no instrumentation, best and median:

| session | stock 1.50.0 | all fixes | change |
|---|---|---|---|
| 60 steps, 8 KB per read (7 runs) | 5.509 / 5.620 s | 4.376 / 4.433 s | **-21.1%** |
| 120 steps, 8 KB per read (3 runs) | 10.945 / 11.053 s | 8.939 / 9.024 s | -18.4% |
| per-step fixes alone, 60 steps | 4.782 / 4.796 s | 4.357 / 4.377 s | -8.7% |

**Equivalence.** `startup/equiv_tokens.py` compares 473 estimates across
plain ASCII, ASCII control characters, Latin-1 accents, CJK, astral emoji,
every code point from 0 to 300 and a block of CJK one character at a time,
plus repeated whole-request estimates to exercise the caches: identical on
both trees. `startup/equiv_wire.py` captures every JSON body the CLI sends
to the stub endpoint across a ten-step session and compares them after
normalising the three fields that vary per run (the timestamp in the system
prompt, the session UUID, and the temp directory): the ten request bodies
are identical.

**What was left on the table, and why.** After these fixes the largest
remaining cost in a long session is the OpenAI SDK's own request transform,
about 45% of the profile, which walks the entire message payload through a
TypedDict-driven conversion on every request. It has exactly the same shape,
per step and proportional to history, and it is inherent to resending the
conversation each turn. Bypassing it means calling below the SDK's public
`create()`, which is version-fragile, so it is reported rather than fixed.

**Why this is the case the cold start was not.** Here the deliverable was a
number the code does not state anywhere: what one more character of
conversation costs on every subsequent step. The fit made that number
trustworthy at 0.1% irregular, the coefficient identified the fix, and
re-deriving the same formula afterwards showed the term collapse by three
orders of magnitude. That is a cost function doing work a profile cannot,
and this time the wall clock moved with it.

## A second codebase, written by an agent: a 111x faster tree walk in spec2lean

`spec2lean` is a specification-to-Lean pipeline whose git history is 70 of 170
commits authored by a coding agent. Phase 1 turns a PDF or HTML specification
into a hierarchical SQLite index; the read-only query commands over that index
are deterministic, offline and pure CPU, which makes them a clean drperf target.
Three prebuilt indexes ship with the repository, of 504, 10,684 and 24,352
nodes, so document size is a state that can be varied without building anything.

The first timing pass over the read-only commands is the reason to look:

```
index stats        0.13 s      index definitions  0.12 s
index xrefs        0.12 s      index dump         0.11 s
index tree        71.80 s      index validate    73.66 s
```

Seventy-one seconds to print a heading hierarchy of 1,400 lines.

**Beat one, the fit.** `_print_tree` walks the tree with two queries per node.
The region is the whole walk; the states are the number of nodes in the subtree
being printed and the number of nodes in the whole document, and
`s2l/pick_nodes.py` tabulates real nodes spanning subtree sizes from 25 to
15,661 so a single index yields a whole sweep.

Declaring both states at once produced a formula drperf itself refused to stand
behind:

```
cost(n_nodes, n_total) = 10,634,764.1*n_nodes + 0*n_total + -1,972,730.6
    blocks: 8007 affine, 981 constant, 1267 irregular (0.3% of cost)
    negative constant: the counts curve over the observed values
                       (n log n, n^2, ...); the plane is a local approximation
```

The per-block test passes at 0.3%, and the tool still says the answer is wrong,
because the fitted constant is negative. Adding the product of the two states as
a third variable did not help either: within one document the product and the
node count are collinear. What does work is one fit per document, which turns
the curvature into a comparison of two slopes:

| document | instructions per heading printed | irregular |
|---|---|---|
| 10,684 nodes | 7,854,576.6 | 0.2% |
| 24,352 nodes | 17,930,326.6 | 0.0% |

**Beat two, the surprise: the slope is the document.** The two slopes stand in
the ratio 2.283; the two documents stand in the ratio 2.279. Printing one
heading costs a pass over the entire specification, so the walk is quadratic.
drperf attributes the slope to `sqlite3VdbeExec`, 4,695,606 instructions per
node inside the SQLite virtual machine, which points at the query rather than
at Python. The query plan is explicit about it:

```
sqlite> explain query plan
        SELECT node_id FROM nodes WHERE parent_id = ? ORDER BY ordinal;
  SCAN nodes USING INDEX nodes_parent_order
  USE TEMP B-TREE FOR ORDER BY
```

`SCAN`, not `SEARCH`. The one index that covers the column is
`nodes(document_id, parent_id, ordinal)`, and a query that constrains only
`parent_id` cannot seek into a composite index whose first column is missing.
So SQLite walks the whole index for every node and then sorts the survivors in
a temporary B-tree.

**Beat three, the fix.** The parent row already carries `document_id`, and no
child in any of the three shipped indexes has a different `document_id` from its
parent (checked: 0 of 35,540 parent/child pairs). Naming it in the query lets
the index seek and makes the ordering free. A second edit stops `SELECT *` from
loading `raw_text` and `normalized_text` in full for every node when `_summary`
reads 100 characters of one of them.

```
- "SELECT node_id FROM nodes WHERE parent_id = ? ORDER BY ordinal", (node_id,)
+ "SELECT node_id FROM nodes WHERE document_id = ? AND parent_id = ? ORDER BY ordinal",
+ (row["document_id"], node_id),

  SEARCH nodes USING INDEX nodes_parent_order (document_id=? AND parent_id=?)
```

**The same formula, re-derived after the fix:**

| document | before | after | factor |
|---|---|---|---|
| 10,684 nodes | 7,854,576.6 | 103,554.5 | 75.8x |
| 24,352 nodes | 17,930,326.6 | 109,027.6 | 164.5x |
| slope ratio between the two documents | 2.283 | 1.053 | |

The slope ratio falling to 1.053 is the statement that the quadratic is gone:
after the fix, printing a heading costs the same whatever the size of the
document it sits in.

**Instructions**, printing a 1,933-node subtree of the 24,352-node index:

| region | calls | before | after | change |
|---|---|---|---|---|
| `children_query` | 1,933 | 34,489,966,352 | 46,038,770 | -99.9% |
| `print_tree` | 1 | 34,671,724,854 | 224,310,841 | -99.4% |
| whole process | | 35,108,938,346 | 661,568,909 | -98.1% |
| per node visited | | 17,936,743 | 116,042 | 155x |

The formula predicted 17,930,327 instructions per node and the run measured
17,936,743, a difference of 0.04%.

**End to end**, the real CLI command, uninstrumented:

| command | stock | fixed | speedup |
|---|---|---|---|
| `index tree` on CXL 2.0 (10,684 nodes) | 10.75 s | 0.47 s | 22.9x |
| `index tree` on PTX 9.3 (24,352 nodes) | 70.00 s | 0.63 s | **111x** |
| `index subtree` on the largest PTX node | 44.94 s | 0.43 s | 104x |

The speedup grows with the document, which is what a removed quadratic looks
like. The index fix alone accounts for almost all of it: PTX `index tree` is
0.70 s with the query fix and 0.63 s with the narrowed `SELECT` as well.

**Equivalence.** `s2l/equiv.py` prints 60 trees, spanning every index, both the
headings-only and all-nodes modes and both depth limits, and digests the output:
identical across the stock tree, the query fix alone, and both fixes. The full
CLI output was then diffed directly on all three indexes, including
`--all-nodes` on CXL, 10,684 lines: identical.

**The same shape, four more times.** Grepping for the pattern the formula
exposed finds four further queries that filter `nodes` on `parent_id` without
`document_id`: `index children` in the CLI, one in the evidence query path and
two in the planner's scope resolution. They were not measured here, but they
cannot use the index either.

**The second quadratic, same loop applied again.** `index validate` was still
about 70 seconds, from a different cause: for every stored HTML anchor it
evaluates `//*[@id=$anchor or @name=$anchor]` against the parsed document, so
899 anchors each scan an 80,491-element DOM. Fitting it needed the product of
the two states before it fit at all, 100% irregular with the states alone and
7.5% with the product, and the formula then reads **5,617.5 instructions per
anchor-element pair**. The loop only asks whether a match exists, so one pass
collecting every `id` and `name` answers all of them. Three further child
queries with the same unusable-index shape as the tree walk were fixed the same
way, using a scalar subquery to supply `document_id`.

**Every affected command, end to end:**

| command | stock | fixed | speedup |
|---|---|---|---|
| `index tree` (PTX, 24,352 nodes) | 73.17 s | 0.69 s | **106x** |
| `index subtree` (largest PTX node) | 49.16 s | 0.48 s | 102x |
| `index tree` (CXL 2.0, 10,684 nodes) | 11.68 s | 0.40 s | 29x |
| `index validate` (PTX) | 72.14 s | 3.41 s | 21x |
| `index build` (PTX, from HTML source) | 69.10 s | 3.89 s | 18x |

`index build` is the tool's primary expensive operation, and a full rebuild from
the HTML source produces the same `semantic_digest` and the same validation
result; comparing the two databases table by table, every content table matches
exactly and only `created_at` timestamps differ. The findings are written up for
the project in `/home/ubuntu/spec2lean/bug_report.md`.

**Why this case is worth the two before it.** The cold-start case found real
work with a profiler and drperf only sized it. The per-step case needed a cost
function to see a coefficient. This one needed the cost function to see that a
*coefficient was not a constant*: the number of instructions per node was itself
proportional to a second state, which is what "quadratic" means and what no
single profile of a single input can show. The tool then refused the flat
formula by reporting a negative constant, which is the same guarantee working
from the other side.

## A third-party library: pricing a quadratic in sqlglot's optimizer, and declining to fix it

The previous cases all ended in a fix. This one ends in a number and a refusal,
which is the other thing a cost function is for: deciding that a change is not
worth making, or not yours to make.

**Finding the target.** `oss/screen.py` and `oss/screen2.py` run eleven
workloads across sqlglot, networkx, Pygments, markdown-it-py, mistune,
jsonschema, docutils and Jinja2 at n, 2n and 4n and report the doubling ratio.
Ten of the eleven are flat at 1.7x to 2.0x. One is not:

```
sqlglot.optimize_n_joins   60   294.39ms   937.55ms  3409.01ms   3.18x 3.64x  <== SUPERLINEAR
```

**The fit.** One region around one `sqlglot.optimizer.optimize` call, states the
join count and its square, swept from 10 to 80 joins:

```
cost(n_joins, n_joins_sq) = 10,950,467.9*n_joins + 484,257*n_joins_sq
                          + 87,961,347.4
    blocks: 6699 affine, 9954 constant, 979 irregular   (1.7% of cost)
```

**The formula extrapolates.** Fitted on 10 to 80 joins, it was then checked at
sizes it never saw:

| joins | predicted | measured | error |
|---|---|---|---|
| 160 | 14,237,015,411 | 14,372,870,280 | +0.9% |
| 240 | 30,609,276,843 | 30,787,546,646 | +0.6% |

A threefold extrapolation to under one percent. It also states the crossover:
the quadratic term passes the linear one at 10,950,467 / 484,257 = **23 joins**,
so below that the optimizer is effectively linear and above it it is not.

**Where it comes from.** Attributing the walked nodes inside `Scope._collect` to
the optimizer rule that triggered them, at 160 joins:

| rule | nodes walked | share |
|---|---|---|
| `merge_subqueries.py` | 1,131,034 | **96.2%** |
| `qualify.py` | 11,659 | 1.0% |
| everything else, seven rules | 33,000 | 2.8% |

And the mechanism is a round trip. `optimize()` sets `isolate_tables=True`,
"needed for other optimizations to perform well", so `isolate_table_selects`
wraps every one of the N joined tables in its own single-use CTE. `merge_ctes`
then merges all N of them back. Each merge calls `_merge_from`, which mutates
the AST and so must invalidate the outer scope's analysis, and then
`_merge_expressions`, which reads `outer_scope.columns` and pays a fresh full
walk of an expression that is itself O(N). N merges times an O(N) walk is the
`n_joins_sq` term. Counted directly:

| joins | query nodes | full re-collects | nodes walked |
|---|---|---|---|
| 40 | 395 | 372 | 82,651 |
| 80 | 795 | 732 | 306,171 |
| 160 | 1,595 | 1,452 | 1,175,611 |

The re-collect count grows linearly and the work grows as the square.

**Why I did not fix it.** The invalidation is not a stray bug: `_merge_from`
really does rewrite the tree before `_merge_expressions` reads it, so the cache
really is stale. Removing the quadratic means maintaining the scope's column
index incrementally across six merge helpers, each of which splices inner
expressions into the outer query. The obvious shortcut, computing the
alias-to-columns map once before the loop, is correct for the isolated-table
pattern that produces this workload and wrong in general, because a CTE may
select from another CTE that is merged later. That is a redesign of a widely
used SQL optimizer on the strength of a plausibility argument, and it belongs to
the maintainers.

**What is available without a fix.** Dropping the one rule is a supported
option, `optimize(..., rules=...)`, and it is worth measuring rather than
guessing:

| joins | all 14 rules | without `merge_subqueries` | speedup |
|---|---|---|---|
| 40 | 150 ms | 69 ms | 2.2x |
| 80 | 464 ms | 140 ms | 3.3x |
| 160 | 1,553 ms | 322 ms | 4.8x |
| 240 | 3,392 ms | 497 ms | 6.8x |

The output is not the same: without the rule the N single-use CTEs survive into
the emitted SQL, which is valid but verbose. So this is a real trade, and the
formula is what lets someone price it: below 23 joins there is nothing to buy,
and at 240 joins it is most of the runtime.

**The baseline for anyone who does attempt it.** The upstream repository at
v30.18.0 was cloned and its suite run as a reference point: 1,245 tests and
19,422 subtests pass, with one unrelated environment failure
(`test_lazy_load`, a missing file). Any fix has that to clear.

**What this case adds.** The three cases before it show a cost function finding
work to remove. This one shows it doing the other half of the job: quantifying a
cost precisely enough to extrapolate threefold within one percent, attributing
96% of it to a single rule, and then supporting the decision *not* to change the
code, plus a measured price for the workaround that exists today. A profile of
one query would have shown time in `walk_in_scope` and none of that.

## libcst: three left-recursive grammar rules, and a 102x parse

**Target.** `libcst` 1.9.0, Meta's concrete syntax tree library for Python. It is the
parser behind large-scale codemods and behind tools that read Python source, so its
parse time is on the critical path of anything that touches a whole repository.

### Finding it

Eleven workloads across eight libraries were screened at n, 2n and 4n
(`oss/screen.py`, `screen2.py`, `screen3.py`, `screen4.py`). Ten were flat. The
interesting comparison was against CPython's own parser on the same input:

| shape, 4x input | libcst | CPython `ast` |
|---|---|---|
| `a + b + c ...` | **9.4x** | 3.8x |
| `a \| b \| c ...` (type union) | **9.7x** | 4.5x |
| `obj.m0().m1()...` (method chain) | **19.2x** | 5.8x |
| `a.b.c.d ...` (attribute chain) | **10.5x** | 3.4x |
| `[a0, a1, ...]` (flat list) | 3.8x | 4.0x |

Flat structures are fine. Everything deeply *left-nested* is quadratic, and CPython
parses the identical text in linear time, so it is not inherent to parsing Python.

### Beat one, the fit

```
$ drperf run --blocks --repeat 2 --state n_terms=50,100,...,300 \
      -o out/libcst_fit -- python oss/run_libcst.py shape=0

cost(n_terms, n_terms_sq) = 122,714.4*n_terms + 1,034.9*n_terms_sq + 2,100,550.4
    blocks: 2958 affine, 12742 constant, 496 irregular   (3.7% of cost)
```

### Beat two, the surprise

A Python profiler cannot see into this: `cProfile` reports 0.026 s of 0.031 s inside
`entrypoints.py:_parse`, a single native call, and stops. drperf attributes the
*quadratic term alone*, by function, across the language boundary:

```
per-n_terms_sq coefficient by function:
     300    _int_free                                        [libc]
     181    <DeflatedExpression as core::clone::Clone>::clone [libcst_native]
     181    __GI___libc_malloc
     124    __free
      71    drop_glue::<DeflatedExpression>                  [libcst_native]
```

The quadratic is a `clone` of the expression built so far, plus the allocator traffic
it causes. The cause is in the grammar:

```rust
#[cache_left_rec]
rule sum() -> Expression
    = a:sum() op:lit("+") b:term() {? make_binary_op(a, op, b) }
    / a:sum() op:lit("-") b:term() {? make_binary_op(a, op, b) }
    / term()
```

`rust-peg` implements left recursion by seed growing: the rule body is re-evaluated
once per operator in the chain, and each growth stores the partial result in the rule
cache, which clones it. Clone of a chain of depth k is O(k), so n operators cost
O(n^2). Nine rules are written this way.

### Beat three, the fix

The textbook transformation, `X = X op Y / Y` becomes `X = Y (op Y)*` folded left,
which builds the identical tree because the fold is left-associative:

```rust
#[cache]
rule sum() -> Expression
    = a:term() rest:(op:(lit("+") / lit("-")) b:term() { (op, b) })* {?
        rest.into_iter().try_fold(a, |acc, (op, b)| make_binary_op(acc, op, b))
    }
```

Applied to three families: the six binary-operator rules, `primary` (attribute, call,
genexp-call and subscript suffixes, folded through a small `PrimaryTail` enum), and
`t_primary`, the same chain grammar used for assignment targets. `t_primary` matters
because a bare `obj.m0().m1()...` statement is first *tried* as an assignment target,
so the chain was parsed quadratically once before the parser backtracked and read it
as an expression.

### The same formula, re-derived after the fix

| shape | stock `n_terms_sq` | fixed `n_terms_sq` |
|---|---|---|
| `a + b + c ...` | 1,034.9 | **-0.134** |
| `obj.m0().m1()...` | 8,458.1 | **0.639** |

The quadratic term is gone, not merely reduced.

### Results

Parse time for a single expression, and the doubling ratio:

| chain length | stock | fixed |
|---|---|---|
| 100 | 14.8 ms | 2.8 ms |
| 200 | 55.6 ms (3.8x) | 5.9 ms (2.1x) |
| 400 | 235.0 ms (4.2x) | 10.7 ms (1.8x) |
| 800 | 1,045.9 ms (4.5x) | 21.8 ms (2.0x) |
| 1,600 | 4,505.3 ms (4.3x) | 44.2 ms (2.0x) |

**102x at 1,600 links**, and the scaling is linear rather than quadratic.

At 800 terms, by shape:

| shape | stock | fixed | speedup |
|---|---|---|---|
| `obj.m0().m1()...` | 1,808.4 ms | 45.0 ms | **40.2x** |
| `a.b.c ...` | 232.9 ms | 17.5 ms | 13.3x |
| `a \| b \| c ...` | 214.3 ms | 24.7 ms | 8.7x |
| `a + b + c ...` | 173.5 ms | 26.0 ms | 6.7x |

And on ordinary real-world Python, 562 files and 7 MB from three unrelated projects
(sqlglot, libcst itself, spec2lean):

| | stock | fixed |
|---|---|---|
| parse whole corpus | 14.560 s | 11.912 s |

**18.2% off real parsing**, with no pathological input anywhere in the corpus.

### Correctness

- **Upstream test suite**: 1,160 passed, 11 skipped, 72 subtests passed. Identical
  to the stock build's result on the same command.
- **Structural equality on real code**: all 562 corpus files parsed with both builds
  and digested with `repr(module)`, libcst's full structural representation. Corpus
  digest `a979ad1387f6b9b5` on both. Not merely equal source after round-tripping,
  the same tree.
- **Round-trip**: 562 of 562 files satisfy `parse_module(src).code == src` on both.

### Reproducing

```bash
git clone --depth 1 --branch v1.9.0 https://github.com/Instagram/LibCST oss/libcst-src
cp -r oss/libcst-src oss/libcst-fix4
python oss/fix_libcst.py oss/libcst-fix4 --primary --t-primary
cd oss/libcst-fix4/native && cargo build --release          # 24 s
cp target/release/liblibcst_native.so ../libcst/native.cpython-312-x86_64-linux-gnu.so
python -m pytest libcst/tests libcst/_nodes/tests -q --ignore=libcst/tests/test_fuzz.py
```

The patch is `libcst_fixes.patch`; the equivalence checker is `oss/equiv_libcst.py`
and the corpus timer is `oss/bench_corpus.py`.

### Why this is the case the others were not

The cold-start case was found with a profiler and drperf only sized it. This one a
Python profiler cannot reach at all: the entire cost is one opaque native call. drperf
counted instructions across the language boundary, separated the linear term from the
quadratic one, and attributed the quadratic *specifically* to `DeflatedExpression::clone`
inside the Rust extension. That named the grammar construct, the construct named the
transformation, and the transformation is worth 102x on a chain, 18.2% on ordinary
code, and provably the same syntax tree.


## FramePack: a constant-cost generator with a quadratic save

FramePack is the most widely used causal video generator, designed so that ordinary
hardware can make long video: it produces a section at a time, and its headline property
is that a section costs the same whether it is the first or the fiftieth. The sampling
loop delivers that. The save in the same loop does not.

Both entry points, `demo_gradio.py` and `demo_gradio_f1.py`, end each section with

    save_bcthw_as_mp4(history_pixels, output_filename, fps=30, crf=mp4_crf)

on the whole accumulated video. Section k re-encodes every frame produced so far, so an
S-section run encodes S(S+1)/2 sections' worth of frames instead of S, and leaves one
MP4 per section on disk.

This is the class of problem where the cost contradicts the code rather than the class
a screening harness finds. Nothing at the call site says the preview costs the whole
video; the loop reads as "generate a section, save a preview". It is invisible on a
short run, where it is 2.5x and looks like ordinary overhead, and the demo defaults
produce exactly that. And it is CPU work, so anyone watching GPU utilisation sees
nothing at all.

### The claim, measured

Encoding is flat at 15.9 ms per frame at FramePack's default 640x640, crf 16, 30 fps,
so all growth is re-encoding:

| video length | sections | frames encoded | as written | written once | waste |
|---|---|---|---|---|---|
| 5 s | 4 | 360 | 5.7 s | 2.3 s | 2.5x |
| 30 s | 25 | 11,700 | 186 s | 14 s | 13x |
| 60 s | 50 | 45,900 | 731 s | 29 s | 25x |
| 120 s | 100 | 181,800 | 2,897 s | 57 s | 50x |

`soft_append_bcthw` grows too, since it copies the whole history each section: 139 ms at
37 frames to 534 ms at 901, with 4.4 GB of float32 pixels resident by the end.

### Two fixes, because the two entry points run in opposite directions

`demo_gradio_f1.py` generates forward. Frames go to one open encoder as soon as blending
can no longer reach them, and are then dropped from `history_pixels`, since what is on
disk cannot change. Output is frame-for-frame identical and peak pixel memory becomes
constant. The file is fragmented per frame and flushed so the preview stays playable
while it is written; it trails by the encoder's lookahead, about one section.

`demo_gradio.py` prepends each section, so frames cannot be appended to one stream.
Each section's settled frames are encoded to their own chunk and the chunks are joined
by copying compressed packets, which never re-encodes. That leaves codec noise at chunk
boundaries, so fidelity was checked against the true pixels instead of against stock.

### Results, CPU

| variant | 4 sections | 8 | 16 | output |
|---|---|---|---|---|
| forward | 2.6x | 4.5x | 8.8x | byte-identical, 0 max per-pixel difference |
| reverse | 2.6x | 4.4x | 7.2x | 14.73 dB against stock's 14.74 dB |

Stock video-writing time grows 3.4x per doubling of length; fixed grows 1.9x. Peak
pixels held drops from the whole video to 33 frames: 154 MB rather than 2.7 GB for a
30-second video, and about 17 GB avoided at two minutes.

### Results, end to end on an A100

The right metric for a video generator is the rate it produces frames, and in those
terms this is not a speedup. It is the removal of a decay.

A 30-second video, 25 steps, 640x608, xformers active, high-VRAM confirmed on both
phases, GPU verified free before each. Stock's rate falls steadily as the video it is
appending to grows; fixed holds flat:

| section | 2 | 7 | 12 | 17 | 22 | 25 |
|---|---|---|---|---|---|---|
| stock | 0.8867 fps | 0.7895 | 0.7171 | 0.6534 | 0.6071 | 0.5816 |
| fixed | 0.9160 fps | 0.9045 | 0.9023 | 0.9023 | 0.9045 | 0.8845 |

**Stock loses 34% of its generation rate inside a single 30-second video.** Fixed holds
0.90 fps, within 3% end to end. Nothing was made faster: the machine stops being asked
to redo work, so the rate FramePack was designed to hold is the rate it holds.

| | stock | fixed |
|---|---|---|
| time | 1,276.9 s | 994.8 s |
| generation rate | 0.7056 fps | 0.9057 fps |
| output files | 25 | 1 |
| disk written | 424.9 MB | 28.9 MB |
| peak host memory | 14,089 MB | 11,883 MB |

**1.28x end to end, 282 seconds saved**, 2.2 GB less host memory, 396 MB never written.

Fitting the measured slope, stock at 38.75 + 0.926 per section against a flat 39.8, the
gain grows with length because the waste is quadratic:

| video | 15 s | 30 s | 60 s | 120 s | 300 s |
|---|---|---|---|---|---|
| gain | 1.12x | 1.28x (measured) | 1.57x | 2.15x | 3.89x |

### What drperf found once the whole host path was covered

The first probe marked one region and confirmed the issue already found by reading. Marking
the whole per-section host path, with the bodies copied line for line from the repository
and only markers added, shows it is not one stage but four. Each one is handed the entire
accumulated video every section, and each carries a coefficient per frame of history:

| region | instructions per frame of history | share | what it is |
|---|---|---|---|
| `save_encode` | 6,121,778 | 96.9% | libx264 re-encoding frames it already encoded |
| `save_to_uint8` | 138,240 | 2.2% | `float32 -> uint8` over the whole history |
| `save_clamp_float` | 46,656 | 0.7% | `clamp` and scale, allocating a float copy of the whole history |
| `blend_concat` | 12,096 | 0.2% | `torch.cat` copying the history to grow it by one section |
| `save_rearrange` | 0 | - | einops returns a view, correctly free |
| `blend_weights` | 0 | - | touches only the overlap, correct |
| `blend_to` | 0 | - | dtype already matches, correct |

Encoding dominates at 97%, but the three tensor passes above it are real and were invisible
in wall-clock next to the codec. Two of the seven regions are correct by construction, and
the derivation says so with a coefficient of exactly zero rather than a small number, which
is what makes the four that are not correct stand out.

The fixed version's report is the cleaner statement. drperf declines to fit `blend_concat`,
`blend_weights` and `blend_to` at all, saying "only 1 state point observed", because the
history handed to them is 33 frames in every section of every run: the state stopped
varying, so there is nothing left to be a function of. And the enclosing region goes from

    stock:  cost = 256,321,014.6*section + 274,238,807.8
    fixed:  cost =          -8.7*section + 288,262,771.5

### A measurement that had to be thrown away

An earlier run of this comparison gave 1.10x, and it was wrong. FramePack's worker leaves
its process alive after finishing, holding 68 GB of GPU memory, so the stock phase was
still resident when the fixed phase started and flipped it into low-VRAM mode with model
offloading. The two phases were not run under the same conditions.

It surfaced only because the generation rate looked too low to be believable, at 0.3 fps
on an A100. That turned out to be a second problem: FramePack looks for sage-attn,
flash-attn or xformers and silently falls back to PyTorch SDPA when none is installed.
Fixing the attention backend raised the baseline to 0.7 fps and, because the wasted
encoding is fixed CPU cost, made the fix worth more rather than less: 1.10x became 1.28x.

Two lessons, both cheap to apply and both nearly missed. A number that looks implausible
for the hardware is usually the measurement rather than the subject. And a comparison
between two phases of the same script needs the machine returned to the same state
between them, which here meant waiting for the GPU to actually be free and recording
which mode each phase chose.

### What the end-to-end run cannot show, and why

The two end-to-end videos differ at 9.41 dB, far more than codec noise. That is not the
fix. Running the unmodified code twice with the same seed gives 19.51 dB between its own
two outputs, while stock against fixed gives 21.41 dB: two runs of stock differ from each
other more than stock differs from fixed. FramePack's generation is not reproducible run
to run on this GPU, so no end-to-end pair could ever have matched. Frame identity is
therefore established on CPU, where the pixels going into the loop are controlled, and
there it is exact.

This is worth stating plainly because it is the trap in this kind of measurement: an
end-to-end diff on a generative pipeline looks like a correctness check and is not one.
The control that distinguishes them costs three short runs.

## Gradio: streaming one token re-processes the whole conversation

Gradio fronts a large share of AI demos, and its most common use is a streaming chat.
Streaming works by advancing a generator one yield at a time; `Blocks.process_api` calls
`postprocess_data` on each yield, and for a chatbot that runs `Chatbot.postprocess` over
the entire message list. The framework then diffs the result against the previous chunk
to discover that only the last message changed, and sends the delta.

The wire payload is small, which is good design. The CPU cost is not: everything before
the diff is proportional to the whole conversation.

### Measured per streamed chunk

drperf, per message already in the conversation:

| stage | instructions per message | what it does |
|---|---|---|
| `_postprocess` loop | 31,611.7 | re-processes every message |
| `model_dump` and glue | ~14,209 | re-serialises every message |
| `diff` | 1,258 | walks all messages to find the one that changed |
| `_check_format` | 939 | re-validates every message |
| `model_build` | 161.5 | rebuilds the Pydantic model |
| total | ~49,500 | |

Every one of those fits with 0.0% to 3.5% irregular, so the linear-in-conversation shape
is not in doubt. In wall time, one chunk costs:

| messages in conversation | 0 | 10 | 40 | 160 |
|---|---|---|---|---|
| per chunk | 0.015 ms | 0.072 ms | 0.243 ms | 1.268 ms |

An 85x rise from an empty chat to an 80-turn one. A 500-token reply at that point spends
0.63 s in postprocessing alone, and it keeps growing with the conversation. Against a
model streaming at 200 tokens per second, where a token is 5 ms, this is 25% overhead
that nobody attributes to the framework.

A second, milder effect: the reply being streamed is itself a growing string, and `diff`
tests `obj2.startswith(obj1)` on it. Per-chunk cost rises 1.70x over a 1,600-chunk reply.
Real, but an order of magnitude smaller than the conversation-length term.

### Not fixed

The honest fix is that the framework already knows what changed, since `diff` computes it,
but it computes it after doing the O(conversation) work rather than before. Making the
streaming path re-process only the changed message is a design change in Gradio's core
rather than a contained patch, and I have not attempted it. Recorded here as a
measurement, not as a fix.

## ComfyUI: the cache costs more than the caching saves

ComfyUI is the most used graph orchestrator for image and video generation, and its
central promise is that re-running a workflow only re-executes what changed. Deciding
what changed means computing a cache key per node, and that is where the time goes.

`CacheKeySetInputSignature.get_node_signature` builds a node's key from a flat list of
every one of its ancestors' immediate signatures, then converts the whole list with
`to_hashable`. `add_keys` does this for every node in the workflow, so the total is
proportional to nodes times depth. It runs on every prompt execution, before any node
does any work, and it is pure Python on the CPU with no model involved.

### Depth, not size

Same node count, three shapes:

| nodes | chain | diamond | wide (no depth) |
|---|---|---|---|
| 100 | 67.8 ms | 80.4 ms | 2.3 ms |
| 200 | 435.8 ms | 523.6 ms | 4.4 ms |
| 400 | 2,016.9 ms | 2,463.1 ms | 9.1 ms |
| 800 | 8,312.4 ms | 10,597.9 ms | 18.2 ms |
| per doubling | 4.1x | 4.3x | 2.0x |

At 800 nodes a deep workflow costs **460x** what a wide one of identical size costs. A
200-node chain, an entirely ordinary ComfyUI workflow, spends 436 ms per run deciding
what to skip.

### drperf

An affine fit in the node count alone leaves 74.4% of the cost irregular, which is the
tool saying the model cannot express what it measured. Declaring the squared state
resolves it:

    cost(n, n_sq) = 56,152.8*n + 318.1*n_sq + -563,031.2     irregular 6.1%

and the breakdown per unit of depth puts 80% of it in one place:

| stage | instructions per unit of depth |
|---|---|
| `to_hashable` | 79,077.5 |
| `immediate_sigs` | 12,434.3 |
| `ancestry` | 7,207.6 |

### The fix, and the bug in the first attempt

Signatures are built bottom-up and memoised: a node's key is its own inputs plus the
already-computed signature of each node it links to, shared by reference. The walk is
iterative so a deep workflow cannot exhaust the stack.

The first attempt passed the assembled structure to `to_hashable`, as the original does,
and the verification caught it immediately: `to_hashable` recognises Mappings and
Sequences, and a frozenset is neither, so every parent signature fell through to the
`Unhashable` sentinel and every key became distinct. It showed up as 1,339 of 1,409
invalidation checks failing, including a downstream node's edit appearing to invalidate
its own ancestors. The key has to be assembled already-hashable instead.

### Verification

What matters is not the key's value but which nodes it treats as equal, and which it
invalidates when one changes. Across 62 workflows, including deliberately duplicated and
deliberately shared subgraphs, and perturbing every node of every workflow in turn:

| check | result |
|---|---|
| equality partition identical | 62 / 62 |
| invalidation set identical | 1,409 / 1,409 |
| ComfyUI's own execution unit tests | 67 passed, identical on both trees |

### Results

| shape, 800 nodes | stock | fixed | |
|---|---|---|---|
| chain | 8,312.4 ms | 4.42 ms | **1,881x** |
| diamond | 10,597.9 ms | 4.66 ms | **2,274x** |
| wide | 18.2 ms | 4.32 ms | 4.2x |

Per-node cost becomes flat at about 5.5 us regardless of shape or size, and every shape
now scales at 2.0x per doubling. The wide case, already linear, still gets 4.2x because
the per-node constant drops. drperf confirms the term is gone rather than reduced:

    stock: cost(n, n_sq) = 56,152.8*n + 318.1*n_sq + -563,031.2
    fixed: cost(n, n_sq) = 41,409.9*n +  0.351*n_sq +   39,287

The quadratic coefficient falls by 906x, and the linear term by 26% as well.

Patch: `comfyui_cachekey.patch`, 53 lines added in one file. Workspace: `comfy/`, with
`probe_cachekey.py`, `drperf_cachekey.py`, `fix_comfy.py` and `verify_comfy.py`.

## Searching for more of the FramePack pattern, and not finding it

The FramePack defect has a shape that can be looked for mechanically: a loop that grows a
variable and, in the same body, hands that whole variable to something that walks all of
it. `oss/../videogen/causal/scan_accum.py` looks for exactly that in an AST, and the test
of it is that it rediscovers both FramePack sites from scratch, having been written
without reference to them.

The generalisation that mattered was to treat any `X = f(..., X, ...)` as growth rather
than a list of known concatenation names. FramePack's accumulator is
`history_pixels = soft_append_bcthw(history_pixels, ...)`, which a search for `torch.cat`
and `append` misses entirely.

Scanned: all of `diffusers` pipelines and modular pipelines, CogVideoX, LTX-Video,
Self-Forcing, FramePack. 84 raw candidates fell to 27 after excluding names bound by the
loop itself and same-line self-assignment, both of which are per-item work rather than
accumulation. Every surviving candidate outside FramePack was read and every one is a
false positive: they are per-item chains such as
`reference_image = reference_image.to(...)` followed by `vae.encode(reference_image)`,
where the variable is rebound each iteration rather than accumulated.

Self-Forcing deserves its own line because it is the closest comparable system, a causal
video model with a streaming demo, and it is clean on every axis checked:

| axis | finding |
|---|---|
| output path | frames are streamed to a queue one at a time, never accumulated |
| generation loop | writes into a preallocated tensor by slice assignment, no growing concat |
| KV cache | bounded, and attention reads a windowed slice rather than the whole buffer |
| cache eviction | the shift-left path exists but `local_attn_size` is -1 in both shipped configs, so it is dead code |
| its one scanner hit | `torch.cat([vae_cache, denoised_pred])` is constant at 6 latents per block, not growing |

So the pattern is rare rather than endemic, which makes FramePack's instance more
interesting rather than less. It is worth recording that the search was run and came back
empty, because the alternative reading of one spectacular find is that such finds are
everywhere, and on this evidence they are not.

## A negative result worth recording: the popular AI stack is clean on these axes

Asked for a big, popular AI system to demonstrate on, four areas of the
HuggingFace stack were screened with the same n / 2n / 4n harness that found
libcst and sqlglot. All four are linear. Recording it because a screening method
is only trustworthy if its misses are reported too.

| area | shapes screened | result |
|---|---|---|
| `tokenizers` 0.23 Rust core | 24: prose, one long word, long digit runs, no spaces, char runs, base64, JSON, code, CJK, whitespace runs, newlines, batch, on GPT-2 BPE and BERT WordPiece | all 1.7-2.2x per doubling |
| `transformers` 5.16 tokenizer wrapper | 11: added tokens, added special tokens, chat templates with and without tokenising, encode, offsets, decode, batch decode, batch padding, id conversion | all linear |
| `transformers.generate()` | per-step host cost against generation length, plain greedy and with `repetition_penalty` and `no_repeat_ngram_size` | flat: 1.37 ms to 1.40 ms per step from 128 to 1,024 new tokens |
| model loading | `from_pretrained` against raw weight read | 0.67 s for a 494M-parameter model, against 0.12 s to read the bytes |

Two of these are places the same bug class really did live historically. A
per-step logits processor that rescans the whole sequence is exactly the shape
found in vLLM case D and in the Kimi CLI per-step case, and it is flat here at
1.03x growth over an eightfold longer generation. The interesting reading is
that the heavily-trafficked AI libraries have had this class squeezed out,
which is why the wins in this document are in a coding agent's startup, an
agent-written index tool, a SQL optimizer and a syntax-tree parser rather than
in a tokenizer or a sampling loop.

## Notes on drperf itself, from these runs

- **Fast marker path mis-pairs an outer Python region around adjacent Rust regions.** In `out/lookup_sites` (default C fast path) `case_invalidate_validate`, a Python region around `invalidate_checked`, whose Rust body opens `ftl_controller_invalidate_validate` and then `ftl_controller_invalidate_apply`, reads 0.9M-1.3M instructions per call with 243k of "marker cost" subtracted, i.e. hundreds of nested triggers: the region's end was lost and it swallowed the rest of the iteration. With `PERFMARK_NO_EXT=1` (`out/lookup_sites_noext`) the same region reads 164.7*fill, four lookups, as expected. The load-engine driver on the branch already carries a comment about this. Slopes are unaffected by the marker path; constants are not comparable across the two paths.
- **`derive --predict` compares a marker-free formula with marker-inclusive counts.** `ftl_directory_stats` predicted from `out/step_admission` at the points of `out/step_admission_120` is reported 24% low; 480 triggers x 582 (the calibrated Rust marker cost that `derive` subtracts from the constant) is three quarters of the gap, the rest is a 23.3 -> 26.8 slope drift. For `case_admission_limit` the subtracted marker cost is 2,222 per call and the gap correspondingly larger. The formulas are right; the comparison should add the marker cost back.
- **Costs that are logarithmic or periodic in a declared state are reported as irregular**, correctly by the spec, and the per-function attribution plus the trace is what identifies them (case 3: B-tree leaf occupancy; hash-table doubling). A declared state for the leaf occupancy is not available from outside the map, so this is a place where the trace, not the formula, carries the finding.
- **A real state can be undeclarable.** The block index's growth schedule depends on tombstones placed by a per-process random hash seed (case 3): the same logical run grows the table at different binds in the two repeats. Declaring a projection of it leaves the coefficient at 0.35 and the share unchanged, which is the right answer; the finding lives in the trace.
- **An outer region's dependence on a state its nested regions do not declare is averaged away.** The client keys per-block counts by (region, its own states, root). `derive` reports an outer region "nested regions included" by adding the nested regions' per-point means back in, but those means are keyed by the nested region's states, so if the nested cost depends on an outer state the inner never declared, every value of that state is merged into one inner point and the dependence vanishes. Case 8's first attempt showed it exactly: a Python region declaring `(blocks, digests)` around `invalidate_blocks`, whose own region declares `blocks`, derived `0*digests` at 0.1% irregular while the trace means grew fivefold with `digests` (`out/digest_scan`; the outer keys in the `.blocks` file total ~160k at every point, the inner keys carry the rest merged over `digests`). The workaround is to measure the inner work in a region of its own, as case 8 does, or to declare the state on the inner region.
- **Slot-table overflow degrades silently into a wrong attribution.** On vLLM (~556k basic blocks) the default 131,072-slot table overflows; overflowed blocks all land in the last slot, so every region reads 83-99.9% irregular attributed to a single unrelated symbol, with only a warning line to say why. A run that overflowed should refuse to derive, or derive should print the overflow count next to the percentages. (`--max-slots` is the fix; the dev CLI's help says the default is 8M while `client/drperf.c:150` says 128K.)
- **A Python region with several states costs about 11k instructions to open, and that lands in the parent region.** The binding's `_split_state` checks each value with `isinstance(v, numbers.Integral)`, an ABC lookup (~0.5 us each), so a four-state `perfmark.region(...)` takes ~3.8 us to construct; the calibration subtracts only the 582-instruction in-region part. For a parent that opens many nested Python regions per call (case E's `process_outputs` around `completion_output` and `request_output`) the parent's constant carries the difference. Aggregates agree with native probes (33.8 us per request per step for the whole output path against 82.6k instructions), but the split between a parent and a nested Python region is approximate by roughly 11k per nested region.
- **A late-attach race can mis-attribute the model forward.** Some `--late` runs print `WARNING: N perfmark_end without matching begin`; in those runs `bf16_dot_with_fp32_arith` shows up at ~5M per call inside a Python region such as `process_outputs`, at 98% irregular. Any run with that warning should be discarded and retried; every vLLM number in this document is from a run with zero such warnings.
- **The client's fast key cache compares region and state-name strings by pointer.** With the Python binding those bytes are reallocated per region, so two regions sharing a root, a state count and identical state values merge into one key: in the Wan runs `sched_step` was recorded as `cfg` (8 triggers instead of 4, with "perfmark_end without matching begin" warnings). Workaround: give every region a unique (state-count, state-values) signature; `videogen/verify_regions.py` checks trigger counts against the code. The fix belongs in `client/drperf.c` (`get_key`): compare contents, not addresses.
- **`derive` drops small states when a large computed state shares the basis.** `lib/derive.py:_solve` treats a column as dependent when its pivot is below `1e-9 * max|A|`. With `sq = seq_len*kv_len` (~6.4e12) declared on the Wan regions, `steps` (column contribution 72) was reported as "a linear function of the earlier states" and its 11.4M-per-step coefficient vanished from `wan_call`; `frames` and `steps` were dropped from `transformer_forward` and `denoise_step` the same way. Scale columns before the solve, or declare large states in coarser units.
- **Blocks that trade off are each irregular though their sum is affine.** Wan's `pp_stack` runs one of two `memcpy` blocks depending on where numpy places the destination; each is exactly `1,151.9*pixels_k` when taken and 0 when not, so the region reads 95.7% irregular while its total is affine to 0.03%. A sum-of-blocks test per function, or merging blocks that are never both non-zero at a point, would catch it.
- **Four states is a hard limit (`KEY_STATES=4`)**, and it binds: `process_outputs` needs two sizes, a first-token flag and an output-kind flag to fit.
- **Late attach can land inside a JIT.** With n-gram speculation the first marker fired during `LLM(...)` construction because `NgramProposer.__init__` calls `propose()`, and numba's compilation became one 6.06-billion-instruction trigger. The driver has to disable the markers until after construction and warm-up.
- **The 128-point cap per region** shows up as soon as a driver interleaves two growing states (`ftl_directory_invalidate` at 120 superblocks kept superblocks 57..120 only). The formula still derives from what was kept, but a driver that wants a specific range has to plan for it.
- **`--late` attaches at the first marker anywhere, including one inside `LLM(...)`.** With the speculative set, `NgramProposer.__init__` calls `propose()`, so the attach landed in the middle of the model build: the run went from 51s to 3m31s and the numba JIT of the n-gram kernel was recorded as one 6.06e9-instruction trigger *inside* `ngram_scan`, taking `ngram_propose` to 99.9% irregular with a formula fitted through it. The fix belongs in the driver, not in drperf, but it is not obvious: swap `perfmark.region` for a null context manager until the engine is built **and warmed up**, then restore it and open the stateless attach region. Any lazily-JIT-ed or lazily-initialised marked path needs this.
- **A region's own-thread count can be dominated by the surrounding OpenMP pool's spin, and the trace only carries the own-thread number.** `gather_logprobs` in `out/vllm_stop` reads 47.9M own-thread instructions per call in the steady state against 1.3M in every other phase, because the region is open while `execute_model`'s thread pool is still spinning; `derive` subtracts "OpenMP runtime waiting" from the formula, and the `show` table's `other-thr` column carries the real parallel work (16.2M, of which 1.18M per row). Summing the `.trace` file's `self` field therefore showed a patch that provably removes half the top-k rows as a 0.0% change, while `show` showed it as -29.1%. The trace should carry the other-thread and the waiting components too, or `self` should be documented as unusable for a threaded region.
- `bin/drperf` no longer crashes on a first region that declares states (fixed on 2026-09-06 while this work ran); the `drperf-dev run --blocks` / `derive` route was kept because it gives the per-function breakdown and `--predict`.
