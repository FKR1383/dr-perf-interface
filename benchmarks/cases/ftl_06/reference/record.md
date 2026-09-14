## Case 6. A hidden quadratic: `_ordered_blocks` clones the block map once per offset

**Where.** `CompactionEngine._ordered_blocks` (`src/integration/vllm/compaction.py:231`)
builds the ordered tuple of a superblock's blocks as
`tuple(int(superblock.blocks[offset]) for offset in range(superblock.nblocks))`.
`superblock.blocks` is a pyo3 getter (`lib.rs:682`) that clones the Rust
`BTreeMap` and converts it to a new Python dict on every access, so the
generator pays one full clone-and-convert per offset: n io-blocks cost n
clones of n entries. It is called from `trigger` (per key), `_candidate`,
`_witness_matches` and `record_bind_digest`, and in three of those four it
runs before the caller's marked region opens, so none of the campaign's
regions ever saw it, and none of them declares `nblocks`.

**What was measured.** `examples/cases/ordered_blocks.py`: one complete
superblock per size in 4..64, twenty calls each, in two regions that both
declare `nblocks` and its square: the real function, and the same loop with
the getter read once, as a prediction and not a change to the code.

```
CASE_REPEAT=1 ./run_case.sh ordered_blocks vllm-ditto/.venv-perf/bin/python examples/cases/ordered_blocks.py

case_ordered_blocks   cost(nblocks, square) = 2,049.7*nblocks + 416.9*square + 4,942.8    (16.1% irregular)
    per-square coefficient by function:
               127.4  PyDict_SetItem
                  55  PyDict_Contains
                45.2  <btree::map::IntoIter<usize, i64>>::dying_next
                  26  PyLong_FromLong
case_ordered_once     cost(nblocks, square) = 1,499.7*nblocks + -0.196*square + 6,363.1   (1.3% irregular)
```

The square term is the clone: 417 instructions per offset-times-entry, and
its attribution is the dict being rebuilt (`PyDict_SetItem`) from the
consumed Rust map (`IntoIter::dying_next`). Read the getter once and the
square coefficient is zero to three decimals.

**What it changed.** At the production superblock of 32 io-blocks the real
call costs about 497k instructions and the one-read form about 54k, nine
times less, for the same tuple. `trigger` and `_candidate` run it once per
completed superblock and `_witness_matches` once per candidate, so a store
that completes a superblock pays it at least twice. This is the largest
single item found on the branch, and it was invisible to the annotation
campaign for a reason worth recording: the regions were placed after the
call, and its cost follows a state (`nblocks`) that no caller thought of as
varying, because in production it never does. A flat state can still be the
one that squares.

It is also the cleanest demonstration here of a computed state: `nblocks`
alone reports a negative constant and an irregular share; declaring the
product `nblocks*nblocks` alongside it makes the region affine with the
square carrying the cost.

---

