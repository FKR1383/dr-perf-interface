## Case 8. `_clear_digests` copies the whole digest table for every retired block

**Where.** `CompactionEngine._drop_key` (`src/integration/vllm/compaction.py:258`)
calls `_clear_digests`, which does `for identity in tuple(self.digests)` and
compares every identity to the key. `invalidate_blocks` calls `_drop_key`
once per retired or rebound block, so retiring b blocks scans the whole table
b times. The branch's region declares `blocks` only, and its driver seeds one
digest per block, so the table's size moved in step with `blocks` and the
scan hid inside the per-block slope (16,735 per block in the sweep).

**What was measured.** `examples/cases/digest_scan.py`: a digest table of
32..4,096 unrelated entries plus one per victim, and `_drop_key` on each
victim in a region declaring the table size (why not `invalidate_blocks`
itself is in the drperf notes below).

```
CASE_REPEAT=1 CASE_BLOCKS=1 CASE_DIGESTS=32,64,128,256,512,1024,2048,4096 CASE_REPS=10 \
  ./run_case.sh drop_key vllm-ditto/.venv-perf/bin/python examples/cases/digest_scan.py

case_drop_key   cost(digests) = 288.4*digests + 7,395.3        [all digests]   0.0% irregular
    per-digests coefficient by function:
                 211  _PyEval_EvalFrameDefault
                  47  PyDict_Clear
                  11  PySequence_Tuple
                   8  _PyUnicode_Equal
```

288 instructions per entry in the table, per block dropped, the interpreter
running the comparison loop. A native timing agrees: `invalidate_blocks` of 8
blocks takes 28 us against 64 digests, 123 us against 512, 881 us against
4,096.

**What it changed.** The digest table holds one entry per bound io-block on
the worker, about 3,800 at the documented pool, so every block retired or
rebound costs about 1.1M instructions here, and a 32-block superblock about
35M, on the store path. That is the largest per-event cost found on the
branch, and the annotation campaign's region reported it at 0% unexplained
because its driver never let the table and the batch differ. An index from
key to identities makes the coefficient zero.

---

