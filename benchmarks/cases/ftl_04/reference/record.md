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

