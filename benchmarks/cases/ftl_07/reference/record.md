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

