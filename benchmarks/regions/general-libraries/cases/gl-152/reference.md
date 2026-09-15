# Selection evidence

Source: [https://github.com/pandas-dev/pandas at `a290443f9e0f1dee4ea6aa9d9a5effb8ba5dbaee`](https://github.com/pandas-dev/pandas/blob/a290443f9e0f1dee4ea6aa9d9a5effb8ba5dbaee/pandas/core/reshape/melt.py#L350-L357). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
