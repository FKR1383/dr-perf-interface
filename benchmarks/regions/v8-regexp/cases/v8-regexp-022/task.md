# Emit character-class range checks

Instrument `v8::internal::regexp::EmitClassRanges` with an empty DRPerf RAII region. This target belongs to the regular-expression compilation phase. The marker measures compiler work while producing RegExp code or bytecode; it does not measure later matching of a subject string.

Suggested bounded workload: Emit matching code for bounded character-class ranges.

Build context: compile V8 at the pinned revision with its documented GN/Ninja workflow. Add `benchmarks/regions/support` to the compiler include path so the patch can resolve `drperf_bench_region.h`, and link the PerfMark implementation that supplies `perfmark_begin_v` and `perfmark_end`. See `case.json` for the concrete test command and validation status; pinned V8 region coverage remains unverified.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
