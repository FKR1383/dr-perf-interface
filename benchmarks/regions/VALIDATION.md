# Collection validation

Checked on 2026-09-14:

- 207 distinct source targets across 51 pinned source files.
- 129 Python regions and 78 C++ regions.
- All source hashes and independent patches verified.
- All patches touch only their declared source file, contain one empty marker,
  and place that marker within the declared source bounds.
- Every Python patch restores the original AST after removing instrumentation.
- Every C++ patch only adds the helper include and a scope marker.
- 14 repository benchmark tests pass, including a compiled C++ helper check for
  zero PCVs and balanced markers through early returns, and a source export
  check that excludes the evaluator reference.

No full V8, vLLM, Wan, CPython, or other upstream build was run for this
collection. Workload triggers are suggestions and remain unverified. No agent
pipeline, large-case benchmark, PCV-discovery accuracy or speedup was measured.
The earlier pilot measurements are described separately in
[benchmarks/VALIDATION.md](../VALIDATION.md).
