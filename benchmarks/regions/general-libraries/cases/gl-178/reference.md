# Selection evidence

Source: [https://github.com/urllib3/urllib3 at `43c68c8b43a9dcb44ed2cf4ec91384ca0d46b37d`](https://github.com/urllib3/urllib3/blob/43c68c8b43a9dcb44ed2cf4ec91384ca0d46b37d/src/urllib3/fields.py#L113-L113). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
