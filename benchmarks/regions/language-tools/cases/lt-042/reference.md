# Selection evidence

Pinned upstream: [sympy/external/gmpy.py](https://github.com/sympy/sympy/blob/117eaf45237de39c9d4518a3b7c715f0484ccea9/sympy/external/gmpy.py) at `117eaf45237de39c9d4518a3b7c715f0484ccea9`. The function scored 41 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
