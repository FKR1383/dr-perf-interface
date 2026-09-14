"""Case: what a store bind costs as the directory grows.

One directory, grown one superblock per bind.  Every bind is both the setup
for the next point and a measurement: bind k sees `superblocks = k-1` and
`blocks = sum of earlier fills`.  Two phases with different fills keep
`blocks` and `superblocks` from moving in step, so drperf can separate them.

Regions of interest (same driver runs against the old clone-the-state
core and the current undo-log core):
  ftl_directory_bind_batch(requests, blocks, superblocks)   whole bind_batch
  ftl_directory_bind_commit / _discover / _rollback           current core only

Env: CASE_STEPS (default 24 per phase), CASE_FILL_A (default 4),
CASE_FILL_B (default 16).
"""

from _ditto_ftl_core import FTLController

from examples.cases.common import Storage, arg, prologue, say, superblock_entries


def main() -> None:
    steps = arg("CASE_STEPS", 24)
    import os as _os

    spec = _os.environ.get("CASE_FILLS")
    if spec:
        fills = [int(x) for x in spec.split(",")]
    else:
        fill_c = arg("CASE_FILL_C", 0)
        fills = [arg("CASE_FILL_A", 4), arg("CASE_FILL_B", 16)]
        if fill_c:
            fills.append(fill_c)
    nblocks = max(fills)
    prologue()
    ftl = FTLController(nblocks, storage=Storage())
    sb = 0
    if arg("CASE_CYCLE", 0):
        # Round-robin the batch sizes so `requests` cycles while the
        # directory grows: phases would make the two move together and
        # neither coefficient could be separated from the other.
        for step in range(steps * len(fills)):
            fill = fills[step % len(fills)]
            plan = ftl.bind_store_batch(superblock_entries(sb, nblocks, fill))
            assert len(plan.placements) == fill
            sb += 1
        stats = ftl.directory.stats()
        say(f"bind_grow cycle steps={steps} fills={fills} final={stats}")
        return
    for fill in fills:
        for _ in range(steps):
            plan = ftl.bind_store_batch(superblock_entries(sb, nblocks, fill))
            assert len(plan.placements) == fill
            sb += 1
    stats = ftl.directory.stats()
    say(f"bind_grow steps={steps} fills={fills} final={stats}")


if __name__ == "__main__":
    main()
