"""Case: invalidate_blocks scans the whole digest table once per retired block.

`_drop_key` -> `_clear_digests` (compaction.py:253) copies every identity in
`self.digests` into a tuple and compares each to the key, for every block
retired. The branch's region declares `blocks` only, and its driver seeds
exactly one digest per block, so the O(digests) scan hides inside the
per-block slope. Here the digest table is varied independently: `digests`
unrelated entries plus one per retired block, so the product shows.
Env: CASE_BLOCKS (default 1,2,4,8), CASE_DIGESTS (default 64,128,256,512),
CASE_REPS (default 8).
"""

import os
import sys
from pathlib import Path

from perfmark import region

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from examples.cases.common import arg, prologue, say  # noqa: E402
from examples.ftl.compaction_regions import (  # noqa: E402
    _Digest,
    _Directory,
    _load_target,
    _worker,
)


def main() -> None:
    blocks_grid = [int(x) for x in os.environ.get("CASE_BLOCKS", "1,2,4,8").split(",")]
    digest_grid = [int(x) for x in os.environ.get("CASE_DIGESTS", "64,128,256,512").split(",")]
    reps = arg("CASE_REPS", 8)
    target = _load_target()
    prologue()
    keep = []
    for _ in range(reps):
        for digests in digest_grid:
            for blocks in blocks_grid:
                engine = target.CompactionEngine(_worker(_Directory()))
                # unrelated digests: distinct keys, never matched
                for j in range(digests):
                    key = f"filler{j}/g0/0"
                    engine.digests[(key, 10_000 + j)] = target._DigestEntry(
                        key, 10_000 + j, 0, (), _Digest(j), 1
                    )
                # one digest per victim block, each under its own key, so
                # every retired block performs its own full scan
                victims = []
                for i in range(blocks):
                    key = f"victim{i}/g0/0"
                    engine.digests[(key, i)] = target._DigestEntry(key, i, 0, (), _Digest(i), 1)
                    engine.block_keys[i] = key
                    victims.append(i)
                # `invalidate_blocks` opens its own Python region, and a Python
                # region nested in a Python region corrupts the outer's block
                # key (see CASES.md, drperf notes), so measure the per-block
                # work it does, `_drop_key`, directly: one call per victim.
                for i in victims:
                    with region("case_drop_key", digests=digests):
                        engine._drop_key(engine.block_keys[i])
                assert len(engine.digests) == digests
                keep.append(engine)
    say(f"digest_scan blocks={blocks_grid} digests={digest_grid} reps={reps}")


if __name__ == "__main__":
    main()
