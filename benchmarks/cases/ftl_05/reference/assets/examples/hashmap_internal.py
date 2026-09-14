"""A dict's cost follows its fill, an internal state the caller cannot declare.

Two regions, each declaring what the caller knows: how many operations (n) and
how many entries the dict holds (size). Lookup cost per key depends on probe
length, set by hash collisions at the current load. Insert cost has a step
wherever CPython resizes the table (at 2/3 load, growing to the next power of
two above 3*used), and whether a batch of n inserts crosses that boundary
depends on the table's remaining headroom, not on `size` itself.
"""
import gc
import sys
from perfmark import region

gc.disable()
with region("hm_prologue"):
    pass

import os
SIZES = [int(x) for x in os.environ.get("HM_SIZES", "40,60,80,100,120,160,200,240,300,340").split(",")]
NS = [int(x) for x in os.environ.get("HM_NS", "8,16,32").split(",")]
REPS = int(os.environ.get("HM_REPS", "20"))

for size in SIZES:
    keys = [f"key-{i}" for i in range(size)]
    for _ in range(REPS):
        for n in NS:
            d = {k: i for i, k in enumerate(keys)}          # fresh table, `size` entries
            with region("hm_lookup", n=n, size=size):
                for k in keys[:n]:
                    d[k]
            # Will these n inserts cross the table's resize point? The dict
            # does not expose its headroom, so ask a copy: the table's byte
            # size changes exactly when it is rebuilt. A resize rehashes every
            # entry, so the state declared is the work it implies, `size`
            # entries moved, and 0 when the batch fits in the headroom.
            probe = dict(d)
            before = sys.getsizeof(probe)
            for j in range(n):
                probe[f"new-{j}"] = j
            rehash = size if sys.getsizeof(probe) != before else 0
            with region("hm_insert", n=n, size=size, rehash=rehash):
                for j in range(n):
                    d[f"new-{j}"] = j
print("done")
