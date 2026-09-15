# Selection evidence

Source: [https://github.com/networkx/networkx at `4e74880b0da01977da79915167c64e5c2af38b47`](https://github.com/networkx/networkx/blob/4e74880b0da01977da79915167c64e5c2af38b47/networkx/algorithms/chordal.py#L398-L418). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
