## Case 5. A container's internal state, in 40 lines of Python

`examples/hashmap_internal.py` isolates the mechanism behind case 3's residue
with a CPython dict. Two regions declare what the caller knows, `n` operations
against a dict of `size` entries:

```python
with region("hm_lookup", n=n, size=size):
    for k in keys[:n]:
        d[k]
with region("hm_insert", n=n, size=size):
    for j in range(n):
        d[f"new-{j}"] = j
```

```
hm_lookup   cost(n, size) = 768.7*n   + 0*size + 1,298.9     0.0% irregular
hm_insert   cost(n, size) = 1,970.2*n + 0*size + 2,624      10.6% irregular
    irregular by function: PyDict_Contains 2,020 | PyDict_SetItem 1,293 | _Py_HashBytes 672
```

`size` has coefficient 0 in both: an operation costs the same in a dict of 40
or 300. The insert residue is the resize, and the per-point means show it as a
step at the sizes whose table happens to be near 2/3 load (80, 160, 340), not
as a slope. The table's headroom is internal to the dict, the exact analogue
of node fill in the B-tree.

Declaring it is possible here because a resize is observable from outside: a
copy's byte size changes exactly when its table is rebuilt.

```python
probe = dict(d); before = sys.getsizeof(probe)
for j in range(n): probe[f"new-{j}"] = j
rehash = size if sys.getsizeof(probe) != before else 0
with region("hm_insert", n=n, size=size, rehash=rehash): ...
```

```
sizes 40..340,  n 8..32:   cost = 2,014.7*n + 5*rehash   + 2,518    6.6% irregular
sizes 20..1500, n 4..64:   cost = 1,957.8*n + 1.7*rehash + 1,428   10.5% irregular
```

Widening the sweep is the check on any such declaration. The workload term
holds (2,015 to 1,958 per insert; the small run predicts the large one within
7%), and the internal-state term does not (5 to 1.7 per entry), because
"entries moved" is a proxy for a cost that is really the new table's slot
count plus a reinsert. A coefficient on a proxy for hidden state is only as
good as the range it was fitted on, and drperf's `--predict` across runs is
what says so.

---

