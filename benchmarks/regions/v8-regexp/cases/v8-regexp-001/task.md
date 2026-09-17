# Compare Latin-1 backreference without case sensitivity

Instrument `v8::internal::regexp::BackRefMatchesNoCase` with an empty DRPerf RAII region. This target belongs to the regular-expression execution phase. The marker measures work performed while executing the selected matching path.

Suggested bounded workload: Execute a case-insensitive Latin-1 backreference comparison of bounded length.

Build context: compile V8 at the pinned revision with its documented GN/Ninja workflow. Add `benchmarks/regions/support` to the compiler include path so the patch can resolve `drperf_bench_region.h`, and link the PerfMark implementation that supplies `perfmark_begin_v` and `perfmark_end`. See `case.json` for the concrete test command and validation status; pinned V8 region coverage remains unverified.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
