"""Bind repeatedly against a directory held at an exact size.

Three rules make this region's cost derivable, and all three are about the
driver rather than the marker:

1. Every call must sit on a state point that REPEATS. A point seen once has a
   mean of one sample, and drperf's 5% per-block tolerance then reads ordinary
   allocator jitter as cost following no state. A directory that grows
   monotonically gives every call its own point, which is why `bind_grow`
   cannot be fitted however its states are declared.
2. The point must be an exact directory size, not a bucket. Bucketing buys
   samples but each bucket then spans many real sizes, so the spread inside a
   point is real variation and lands in the same place.
3. The calls that BUILD the fixture must not dominate the calls being
   measured, because the build is where the block index doubles, and which
   pass pays for a doubling is not deterministic. So the fixture is built once
   per repetition and then reused for many measured binds, and the build uses
   a batch size the measurement never uses.

Env: CASE_SIZES (default 8,16,24,32), CASE_FILLS (default 4,8,16,24),
CASE_REPS (default 6), CASE_INNER (default 50).
"""

import os

from _ditto_ftl_core import FTLController

from examples.cases.common import Storage, arg, prologue, say, superblock_entries

NBLOCKS = 32


def main() -> None:
    sizes = sorted(
        (int(x) for x in os.environ.get("CASE_SIZES", "8,16,24,32").split(",")),
        reverse=True,
    )
    fills = [int(x) for x in os.environ.get("CASE_FILLS", "4,8,16,24").split(",")]
    reps = arg("CASE_REPS", 6)
    inner = arg("CASE_INNER", 50)
    prologue()
    top = max(sizes)
    scratch = top + 1
    scratch_key = f"s/g0/{scratch}"
    for _ in range(reps):
        ftl = FTLController(NBLOCKS, storage=Storage())
        # Build to the largest size once. The block index reaches its final
        # capacity here, so no measured bind can be the one that grows it.
        for sb in range(top):
            ftl.bind_store_batch(superblock_entries(sb, NBLOCKS, NBLOCKS))
        live = top
        for size in sizes:
            while live > size:
                live -= 1
                victims = [
                    (lb, f"s/g0/{live}")
                    for lb, *_ in superblock_entries(live, NBLOCKS, NBLOCKS)
                ]
                assert len(ftl.invalidate_checked(victims)) == NBLOCKS
            # One scratch superblock, then REBIND it. A rebind replaces the
            # same offsets, so the directory neither grows nor shrinks and
            # every measured call sees exactly `size + 1` superblocks. The
            # alternative, bind then invalidate, costs one invalidate trigger
            # per block and swamps the run without changing what is measured.
            # Measure the same operation the build performs: create a
            # superblock and prune one. Binding the same logical blocks under
            # a different owner unmaps them from the previous superblock,
            # which empties and is pruned, so the directory holds `size + 1`
            # throughout and every measured call has the shape of a real
            # store. Rebinding the SAME key instead would measure a replace,
            # a structurally different path that no single plane covers
            # together with the build's creates.
            ftl.bind_store_batch(superblock_entries(scratch, NBLOCKS, max(fills), "a"))
            resident = size + 1
            assert ftl.directory.stats()["superblocks"] == resident
            owners = ("b", "a")
            for step in range(inner):
                for fill in fills:
                    plan = ftl.bind_store_batch(
                        superblock_entries(scratch, NBLOCKS, fill, owners[step % 2])
                    )
                    assert len(plan.placements) == fill
                    ftl.bind_store_batch(
                        superblock_entries(
                            scratch, NBLOCKS, max(fills), owners[(step + 1) % 2]
                        )
                    )
            assert ftl.directory.stats()["superblocks"] == resident
    say(f"bind_at_size sizes={sizes} fills={fills} reps={reps} inner={inner}")


if __name__ == "__main__":
    main()
