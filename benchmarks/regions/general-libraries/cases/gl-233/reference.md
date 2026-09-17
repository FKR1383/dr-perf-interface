# Selection evidence

Source: [https://github.com/python-attrs/attrs at `8f767776326faaed11e6c2974798787f6e19b343`](https://github.com/python-attrs/attrs/blob/8f767776326faaed11e6c2974798787f6e19b343/src/attr/_make.py#L3311-L3317). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
