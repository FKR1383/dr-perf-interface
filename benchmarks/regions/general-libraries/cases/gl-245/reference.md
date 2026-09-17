# Selection evidence

Source: [https://github.com/cpburnz/python-pathspec at `f0fb3f4aaaca490d7667e4dc1d565d52a25158b0`](https://github.com/cpburnz/python-pathspec/blob/f0fb3f4aaaca490d7667e4dc1d565d52a25158b0/pathspec/util.py#L613-L618). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
