"""Bind cost over a GRID of batch size x directory size, every point repeated.

Case 3 asks how a bind's cost varies with the directory it runs against, so
holding the directory at one size and fitting `requests` alone answers a
different, easier question. Both states have to vary independently and every
combination has to repeat.

The measured call is always the same operation: bind the SAME logical blocks
under the other owner. That unmaps every one of them from the current scratch
superblock, which empties and is pruned, and creates the new one, so the
directory holds exactly `size + 1` superblocks at the entry of every measured
call, whatever the batch size. Batch size and directory size are therefore
independent, and neither is confounded with the other.

Env: CASE_SIZES (default 8,16,24,32), CASE_FILLS (default 4,8,12,16,20,24),
CASE_INNER (default 100).
"""

import os

from _ditto_ftl_core import FTLController

from examples.cases.common import Storage, arg, prologue, say, superblock_entries

NBLOCKS = 32


def main() -> None:
    sizes = sorted(int(x) for x in os.environ.get("CASE_SIZES", "8,16,24,32").split(","))
    fills = [int(x) for x in os.environ.get("CASE_FILLS", "4,8,12,16,20,24").split(",")]
    inner = arg("CASE_INNER", 100)
    prologue()
    ftl = FTLController(NBLOCKS, storage=Storage())
    scratch = max(sizes) + 1
    built = 0
    for size in sizes:
        # Grow to this size once; the fixture is shared by every fill below.
        while built < size:
            ftl.bind_store_batch(superblock_entries(built, NBLOCKS, NBLOCKS))
            built += 1
        assert ftl.directory.stats()["superblocks"] == size
        for fill in fills:
            blocks = superblock_entries(scratch, NBLOCKS, fill, "a")
            ftl.bind_store_batch(blocks)
            assert ftl.directory.stats()["superblocks"] == size + 1
            for step in range(inner):
                owner = "b" if step % 2 == 0 else "a"
                plan = ftl.bind_store_batch(
                    superblock_entries(scratch, NBLOCKS, fill, owner)
                )
                assert len(plan.placements) == fill
                # The previous scratch superblock lost every block it had, so
                # it was pruned: the count is back where it started.
                assert ftl.directory.stats()["superblocks"] == size + 1
            last = "a" if inner % 2 == 0 else "b"
            victims = [
                (lb, f"{last}/g0/{scratch}")
                for lb, *_ in superblock_entries(scratch, NBLOCKS, fill, last)
            ]
            assert len(ftl.invalidate_checked(victims)) == fill
            assert ftl.directory.stats()["superblocks"] == size
    say(f"bind_grid sizes={sizes} fills={fills} inner={inner}")


if __name__ == "__main__":
    main()
