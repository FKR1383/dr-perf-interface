# Selection evidence

Pinned upstream: [pyparsing/helpers.py](https://github.com/pyparsing/pyparsing/blob/efd56db4e59f36b1673ce0eb0823e3afaa9d1201/pyparsing/helpers.py) at `efd56db4e59f36b1673ce0eb0823e3afaa9d1201`. The function scored 293 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
