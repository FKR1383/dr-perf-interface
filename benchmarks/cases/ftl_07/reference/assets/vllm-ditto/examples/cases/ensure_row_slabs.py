"""Case: ensure_row scans every exhausted slab before it finds a free slot.

HandleManager::alloc_row_slot (handle_manager.rs) walks `slabs_by_size[row]`
in order, looking up each slab in a BTreeMap to test whether it still has a
free slot. Full slabs are only removed from that list when their last row is
freed, so as the pool fills the walk grows by one slab per slab filled, and
every io-block row materialised by a store pays it. Nothing marks
`ensure_row`, so this is a Python region around each call declaring the one
state the code makes it depend on: how many slabs are already full.
Env: CASE_ROWS (default 240), CASE_SLOTS (rows per slab, default 4),
CASE_REPS (default 6).
"""

from _ditto_ftl_core import FreshAllocator, HandleManager
from perfmark import region

from examples.cases.common import arg, prologue, say

CHUNK_BYTES = 1 << 16


def main() -> None:
    rows = arg("CASE_ROWS", 240)
    slots = arg("CASE_SLOTS", 4)
    reps = arg("CASE_REPS", 6)
    row_bytes = CHUNK_BYTES // slots
    prologue()
    keep = []
    for _ in range(reps):
        manager = HandleManager(
            (rows // slots + 4) * CHUNK_BYTES, chunk_bytes=CHUNK_BYTES, pin=False
        )
        fresh = FreshAllocator(manager, row_bytes, rows)
        handle = fresh.allocate("rows")
        locked = manager.write_lock(handle)
        for row in range(rows):
            # The first row of every slab creates it (new_slab: a walk of the
            # free chunk set for a contiguous run); the rest draw a slot.
            with region(
                "case_ensure_row", full_slabs=row // slots, new_slab=int(row % slots == 0)
            ):
                span = locked.ensure_row(row * row_bytes)
            keep.append(span)
        locked.unlock()
        keep.append((manager, fresh))
    say(f"ensure_row rows={rows} slots_per_slab={slots} reps={reps}")


if __name__ == "__main__":
    main()
