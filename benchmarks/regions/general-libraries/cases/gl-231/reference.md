# Selection evidence

Source: [https://github.com/python-jsonschema/jsonschema at `865c27fc3df08a082740d7743583795235fdfe81`](https://github.com/python-jsonschema/jsonschema/blob/865c27fc3df08a082740d7743583795235fdfe81/jsonschema/_utils.py#L86-L90). The pristine snapshot is retained with its SHA-256 in `case.json`.

The selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.
