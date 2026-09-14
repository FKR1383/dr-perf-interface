"""Print a digest of plan_load / invalidate_checked / bind_store_batch results
on a seeded random workload.  Run under two builds; the digests must match."""

import hashlib
import random

from _ditto_ftl_core import FTLController

from examples.cases.common import Storage

rng = random.Random(7)
NBLOCKS = 8
ftl = FTLController(NBLOCKS, storage=Storage())
h = hashlib.sha256()
live = set()
for step in range(400):
    op = rng.random()
    if op < 0.5:
        sb = rng.randrange(40)
        fill = rng.randrange(1, NBLOCKS + 1)
        entries = [
            (sb * NBLOCKS + off, "o%d" % rng.randrange(3), 0, sb * NBLOCKS + off, (sb * NBLOCKS + off) * 256, bool(rng.randrange(2)))
            for off in rng.sample(range(NBLOCKS), fill)
        ]
        try:
            plan = ftl.bind_store_batch(entries)
        except ValueError as exc:
            h.update(("bind-error %s" % exc).encode())
            continue
        live.update(e[0] for e in entries)
        h.update(repr([(p.handle, p.offset) for p in plan.placements]).encode())
        h.update(repr(sorted(plan.trigger_keys)).encode())
    elif op < 0.8 and live:
        wanted = rng.sample(sorted(live), min(len(live), rng.randrange(1, 12)))
        wanted += [rng.randrange(1000, 1100)]  # one unmapped block
        plan = ftl.plan_load({0: [(lb, lb) for lb in wanted]})
        h.update(repr([(r.group, r.handle, r.blocks, r.skip, r.count, r.destinations, r.position_base) for r in plan.reads]).encode())
        h.update(repr((sorted(plan.unmapped), sorted(plan.trigger_keys))).encode())
    elif live:
        victims = rng.sample(sorted(live), min(len(live), rng.randrange(1, 6)))
        invs = []
        for lb in victims:
            found = ftl.directory.lookup(lb)
            key = found[0].key if found is not None and rng.random() < 0.7 else "stale/g0/0"
            invs.append((lb, key))
        applied = ftl.invalidate_checked(invs)
        live.difference_update(applied)
        h.update(repr(sorted(applied)).encode())
print("digest", h.hexdigest()[:16], "stats", sorted(ftl.directory.stats().items()), "counters", sorted(ftl.stats.items()))
