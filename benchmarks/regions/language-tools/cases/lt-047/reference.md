# Selection evidence

Pinned upstream: [sqlglot/tokenizer_core.py](https://github.com/tobymao/sqlglot/blob/3ca824895ef423f7895fb13d72357548c0f1f367/sqlglot/tokenizer_core.py) at `3ca824895ef423f7895fb13d72357548c0f1f367`. The function scored 209 in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.
