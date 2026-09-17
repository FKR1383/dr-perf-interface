"""Case: ftl.count() round-trips the whole stats dict through Python.

PyFTLController::count pulls every (name, value) of the Python dict into the
Rust map, bumps one counter, then rewrites the whole dict (lib.rs pull_stats /
sync_stats).  The cost follows the number of distinct counters, a state no
caller of count() thinks about.  Env: CASE_REPS (default 10).
"""

from _ditto_ftl_core import FTLController
from perfmark import region

from examples.cases.common import Storage, arg, prologue, say

ENTRIES = (4, 8, 16, 32, 64)


def main() -> None:
    reps = arg("CASE_REPS", 10)
    prologue()
    controllers = []
    for n in ENTRIES:
        ftl = FTLController(32, storage=Storage())
        ftl.stats.update({f"counter_{i}": i for i in range(n)})
        controllers.append((n + len(ftl.stats) - n, ftl))
    for _ in range(reps):
        for entries, ftl in controllers:
            with region("case_count", entries=entries):
                ftl.count("stores")
    say(f"count_stats entries={[e for e, _ in controllers]} reps={reps}")


if __name__ == "__main__":
    main()
