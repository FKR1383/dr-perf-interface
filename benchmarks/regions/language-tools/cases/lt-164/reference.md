# Selection evidence

Pinned upstream: [src/jinja2/nodes.py](https://github.com/pallets/jinja/blob/5ef70112a1ff19c05324ff889dd30405b1002044/src/jinja2/nodes.py) at `5ef70112a1ff19c05324ff889dd30405b1002044`. The function scored 67 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
