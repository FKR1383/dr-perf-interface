"""Case: the per-step admission limit is a full scan of the directory.

The connector calls ftl.admission_limit() once per scheduler step
(connector.py build_connector_worker_meta -> controller.rs admission_limit
-> directory.stats()).  This driver plays that loop: one store job per step
while the pool fills (each store completes one 32-block superblock), one
admission_limit() per step, then the pool drains one superblock per step.

Regions of interest:
  ftl_directory_stats(superblocks)            Rust, inside stats()
  case_admission_limit(superblocks)           Python, the whole per-step call
  ftl_directory_bind_commit / ftl_directory_invalidate  the regions whose
    counts and states should relate to stats.superblocks exactly.

Env: CASE_SUPERBLOCKS (default 48), CASE_FILL (default 32).
"""

from _ditto_ftl_core import FTLController
from perfmark import region

from examples.cases.common import (
    Storage,
    arg,
    prologue,
    say,
    superblock_entries,
    superblock_key,
)


def main() -> None:
    n_superblocks = arg("CASE_SUPERBLOCKS", 48)
    fill = arg("CASE_FILL", 32)
    prologue()
    ftl = FTLController(fill, storage=Storage())
    resident = 0
    limits = []
    # fill: one completed superblock per step, one admission check per step
    for sb in range(n_superblocks):
        plan = ftl.bind_store_batch(superblock_entries(sb, fill, fill))
        assert len(plan.placements) == fill
        resident += 1
        with region("case_admission_limit", superblocks=resident):
            limits.append(ftl.admission_limit())
    assert limits[-1] == n_superblocks * fill, limits[-1]
    # drain: retire one superblock per step (its last block frees it)
    for sb in range(n_superblocks):
        key = superblock_key(sb)
        applied = ftl.invalidate_checked(
            [(lb, key) for lb, *_ in superblock_entries(sb, fill, fill)]
        )
        assert len(applied) == fill
        resident -= 1
        with region("case_admission_limit", superblocks=resident):
            limits.append(ftl.admission_limit())
    assert limits[-1] == 0
    say(f"step_admission superblocks={n_superblocks} fill={fill} steps={len(limits)}")


if __name__ == "__main__":
    main()
