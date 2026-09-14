# Parse interval quantifier

Instrument `v8::internal::regexp::ParserImpl::ParseIntervalQuantifier` with an empty DRPerf RAII region. This target belongs to the regular-expression parsing phase. The marker measures parser work while constructing the RegExp representation; it does not measure compilation or later matching.

Suggested bounded workload: Parse a bounded interval quantifier such as `{2,8}`.

Build context: compile V8 at the pinned revision with its documented GN/Ninja workflow. Add `benchmarks/regions/support` to the compiler include path so the patch can resolve `drperf_bench_region.h`, and link the PerfMark implementation that supplies `perfmark_begin_v` and `perfmark_end`. See `case.json` for the concrete test command and validation status; pinned V8 region coverage remains unverified.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
