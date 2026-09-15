# Selection evidence

Pinned upstream: [libcst/_nodes/deep_equals.py](https://github.com/Instagram/LibCST/blob/d9a255843b5cdbecc6834684d233bce1f2987f9d/libcst/_nodes/deep_equals.py) at `d9a255843b5cdbecc6834684d233bce1f2987f9d`. The function scored 57 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
