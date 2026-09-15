# Selection evidence

Pinned upstream: [Cython/Plex/Regexps.py](https://github.com/cython/cython/blob/dbbbdbb97f116c46495b5ab88ba0195a277016f9/Cython/Plex/Regexps.py) at `dbbbdbb97f116c46495b5ab88ba0195a277016f9`. The function scored 54 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
