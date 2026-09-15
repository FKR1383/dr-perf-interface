# Selection evidence

Pinned upstream: [Cython/Compiler/Main.py](https://github.com/cython/cython/blob/dbbbdbb97f116c46495b5ab88ba0195a277016f9/Cython/Compiler/Main.py) at `dbbbdbb97f116c46495b5ab88ba0195a277016f9`. The function scored 37 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
