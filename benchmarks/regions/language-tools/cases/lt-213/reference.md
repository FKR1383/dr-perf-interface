# Selection evidence

Pinned upstream: [lark/parser_frontends.py](https://github.com/lark-parser/lark/blob/9a4fb9c7458e8155636773a3cded0016d52516da/lark/parser_frontends.py) at `9a4fb9c7458e8155636773a3cded0016d52516da`. The function scored 74 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
