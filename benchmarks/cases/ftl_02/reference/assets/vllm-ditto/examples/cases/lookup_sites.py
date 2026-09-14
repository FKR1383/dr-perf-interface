"""Case: three call sites pay for a clone of the superblock they touch.

Directory::lookup and Directory::superblock return a clone of the
Superblock (its `blocks` BTreeMap has one entry per resident io-block).
Three controller paths call them once per request just to read a key or
two booleans:
  plan_load            lookup() per requested block, + one clone per key
  invalidate_checked   lookup() per invalidation, to compare the key
  bind_store_batch     superblock() per trigger key, to read two booleans

Each site is measured at a fixed request count while the touched
superblock's fill varies, in a Python region that declares `fill`:
  case_plan_load(fill), case_invalidate_validate(fill), case_bind_trigger(fill)

The invalidations carry a wrong key so nothing is applied and the directory
is unchanged; the bind re-binds an existing block at its own offset so the
fill is unchanged.  Env: CASE_REQUESTS (default 4), CASE_REPS (default 5),
CASE_FILLS (default 8,16,32,64,128,256).
"""

import os

from _ditto_ftl_core import FTLController
from perfmark import region

from examples.cases.common import Storage, arg, prologue, say, superblock_entries


def main() -> None:
    requests = arg("CASE_REQUESTS", 4)
    reps = arg("CASE_REPS", 5)
    fills = tuple(int(x) for x in os.environ.get("CASE_FILLS", "8,16,32,64,128,256").split(","))
    nblocks = max(fills)
    prologue()
    directories = []
    for fill in fills:
        ftl = FTLController(nblocks, storage=Storage())
        plan = ftl.bind_store_batch(superblock_entries(0, nblocks, fill))
        assert len(plan.placements) == fill
        directories.append((fill, ftl))
    destinations = [object() for _ in range(requests)]
    keep = []
    for _ in range(reps):
        for fill, ftl in directories:
            wanted = [(lb, destinations[i]) for i, (lb, *_) in enumerate(superblock_entries(0, nblocks, requests))]
            with region("case_plan_load", fill=fill):
                plan = ftl.plan_load({0: wanted})
            assert len(plan.reads) == 1 and plan.reads[0].count == requests
            stale = [(lb, "stale/g0/0") for lb, *_ in superblock_entries(0, nblocks, requests)]
            with region("case_invalidate_validate", fill=fill):
                applied = ftl.invalidate_checked(stale)
            assert applied == []
            rebind = superblock_entries(0, nblocks, 1)
            with region("case_bind_trigger", fill=fill):
                plan = ftl.bind_store_batch(rebind)
            assert len(plan.placements) == 1
            keep.append(plan)
    say(f"lookup_sites requests={requests} reps={reps} fills={fills}")


if __name__ == "__main__":
    main()
