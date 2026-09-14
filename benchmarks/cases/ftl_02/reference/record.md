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

