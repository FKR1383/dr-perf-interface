# Selection evidence

Pinned upstream: [astroid/bases.py](https://github.com/pylint-dev/astroid/blob/5d1a0a2efabdc43f6cb8449375476b2915ede8fe/astroid/bases.py) at `5d1a0a2efabdc43f6cb8449375476b2915ede8fe`. The function scored 150 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
