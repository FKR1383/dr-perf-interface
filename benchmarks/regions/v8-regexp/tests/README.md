# V8 RegExp test cases

Every case has a self-contained `tests/test_case.js` with bounded inputs and correctness assertions. Run the command recorded in that case's `case.json` from the case directory, replacing `{d8}` with the instrumented V8 shell path.

Classic execution and parser candidates use `--regexp-interpret-all`. This forces classic matching through RegExp bytecode and avoids later native RegExp compilation. Classic compiler candidates use `--regexp-jit-all`, which requests immediate native RegExp compilation. Experimental compiler and interpreter candidates use `--enable-experimental-regexp-engine --default-to-experimental-regexp-engine` so supported patterns select the experimental engine. These flags are defined in the pinned revision's [`src/flags/flag-definitions.h`](https://chromium.googlesource.com/v8/v8.git/+/736a2cbec441e85b68c742215d15318abfeae707/src/flags/flag-definitions.h).

The tests exercise candidate JavaScript paths. A successful assertion run establishes behavior only. Confirming a particular internal region requires running the patched, instrumented `d8` and observing the corresponding DRPerf marker.

The test files have no external dependencies. Four Unicode-sets parser tests
require the `v` flag. They fail explicitly on runtimes that do not implement
it; a skipped input is not a passing test. The other 24 tests pass their value
assertions on host Node.js 18.19.1, which does not establish pinned V8 coverage.
