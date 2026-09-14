# V8 RegExp source regions

This collection contains 28 empty-marker regions from V8's regular-expression implementation, pinned to revision `736a2cbec441e85b68c742215d15318abfeae707`.

| Phase | Cases | Main source files |
| --- | ---: | --- |
| RegExp execution | 6 | `src/regexp/regexp-interpreter.cc`, `src/regexp/experimental/experimental-interpreter.cc` |
| RegExp parsing | 13 | `src/regexp/regexp-parser.cc` |
| RegExp compilation | 9 | `src/regexp/regexp-compiler.cc`, `src/regexp/experimental/experimental-compiler.cc` |

Each patch includes `drperf_bench_region.h`. When building the patched V8 source, add `benchmarks/regions/support` to the compiler include path and link the PerfMark implementation that provides `perfmark_begin_v` and `perfmark_end`. The shared helper is [`../support/drperf_bench_region.h`](../support/drperf_bench_region.h).

The snapshots are pristine upstream files. Apply each case's patch independently from the repository root represented by its `source.path`. Build commands and workloads have not been verified.
