"""Case: CompactionEngine._ordered_blocks re-reads `superblock.blocks` per offset.

`PySuperblock.blocks` is a getter that clones the block map and builds a new
Python dict on every access (lib.rs). `_ordered_blocks` indexes it inside a
generator over `range(nblocks)`, so a complete superblock of n io-blocks pays
n clones of n entries: n^2 conversions for an n-tuple. The callers' regions
declare pages/blocks/keys; none declares nblocks, and none can express the
square. Two regions per size: the real function, and the same loop reading the
getter once (a prediction, not a change to the code).
Env: CASE_SIZES (default 4,8,12,16,24,32,48,64), CASE_REPS (default 20).
"""

import importlib.util
import os
import sys
from pathlib import Path

from _ditto_ftl_core import FTLController
from perfmark import region

from examples.cases.common import Storage, arg, prologue, say, superblock_entries

ROOT = Path(__file__).resolve().parents[2]


def load_engine():
    spec = importlib.util.spec_from_file_location(
        "_ordered_blocks_target", ROOT / "src/integration/vllm/compaction.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.CompactionEngine


def main() -> None:
    sizes = [int(x) for x in os.environ.get("CASE_SIZES", "4,8,12,16,24,32,48,64").split(",")]
    reps = arg("CASE_REPS", 20)
    engine = load_engine()
    prologue()
    fixtures = []
    for n in sizes:
        ftl = FTLController(n, storage=Storage())
        ftl.bind_store_batch(superblock_entries(0, n, n))  # one complete superblock
        sb = ftl.directory.superblock("s/g0/0")
        assert sb.complete and sb.nblocks == n
        fixtures.append((n, ftl, sb))
    keep = []
    for _ in range(reps):
        for n, _ftl, sb in fixtures:
            with region("case_ordered_blocks", nblocks=n, square=n * n):
                out = engine._ordered_blocks(sb)
            assert len(out) == n
            with region("case_ordered_once", nblocks=n, square=n * n):
                blocks = sb.blocks
                once = tuple(int(blocks[o]) for o in range(int(sb.nblocks)))
            assert once == out
            keep.append((out, once))
    say(f"ordered_blocks sizes={sizes} reps={reps}")


if __name__ == "__main__":
    main()
