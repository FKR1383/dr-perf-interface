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

