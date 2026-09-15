# Selection evidence

Source: [https://github.com/pypa/packaging at `10590c194edb33c82f84a127883d6097c56b7840`](https://github.com/pypa/packaging/blob/10590c194edb33c82f84a127883d6097c56b7840/src/packaging/_ranges.py#L724-L741). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
