# Selection evidence

Source: [https://github.com/psf/requests at `dae7ef63b4df6eded86637f251fc4e3a06c3b479`](https://github.com/psf/requests/blob/dae7ef63b4df6eded86637f251fc4e3a06c3b479/src/requests/cookies.py#L500-L514). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
