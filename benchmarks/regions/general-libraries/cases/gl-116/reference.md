# Selection evidence

Source: [https://github.com/numpy/numpy at `d8c7dad6638b623b79da658cafd9a86c8717630e`](https://github.com/numpy/numpy/blob/d8c7dad6638b623b79da658cafd9a86c8717630e/numpy/lib/_histograms_impl.py#L812-L893). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
