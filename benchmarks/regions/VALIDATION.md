# Collection validation

Checked on 2026-09-14:

- 207 distinct source targets across 51 pinned source files: 129 Python and 78 C++.
- All 207 have concrete bounded test inputs, correctness assertions, and runnable
  argument lists. PCV annotations remain empty.
- Source hashes, test resource hashes, and all independent patches pass the
  collection checker with `--require-tests`.
- Every patch touches only its declared source file and adds one empty marker
  within its declared bounds. Removing Python instrumentation restores the
  original AST; C++ patches only add the helper include and scope marker.
- All 16 repository benchmark tests pass, including an exported Python workload
  that must reach its marker and a compiled C++ helper test for zero PCVs and
  balanced entry/exit through early returns.

## Workload validation

| Group | Region verified | Behavior checked only | Not successfully verified |
| --- | ---: | ---: | ---: |
| accidental-quadratic | 21 | 0 | 0 |
| v8-interpreter | 0 | 46 | 4 |
| v8-regexp | 0 | 24 | 4 |
| vllm | 25 | 0 | 42 |
| wan | 41 | 0 | 0 |
| Total | 87 | 70 | 50 |

`region-verified` means correctness assertions passed and the named empty
marker was observed in the pinned patched source. The Python probe replaces
only instrumentation during native checks; it does not count instructions.
When `DRPERF` is set, it also forwards markers to PerfMark.

The accidental-quadratic drivers exercise bounded size sweeps and controls.
Wan uses tiny random CPU models with fixed seeds and three configurations per
case, without downloading model weights. Verified vLLM direct tests exercise
queues, requests, list removal, penalties, CPU sampling, speculative decoding,
and inherited CPU model-runner methods. Other vLLM tests
use a locally cached small model; each manifest records whether the scenario
and its exact target entry have been checked.

The JavaScript assertions were exercised under Node 18.19.1. This does not
verify coverage of the pinned V8 internal C++ regions. Four RegExp Unicode Sets
cases require the `v` flag unsupported by that host and explicitly fail there;
their declared commands use the pinned `d8` build. Four runtime tests also
require unsupported resource-management syntax or `toWellFormed` and fail
explicitly on that host. All V8 region-entry checks
remain pending an instrumented build.

No full upstream build, agent evaluation pipeline, large-case performance
benchmark, PCV-discovery accuracy, cost-model validation, or speedup measurement
was performed in this collection update. Small test inputs provide starting
workloads for later experiments; they do not establish extrapolation to larger
inputs. The earlier pilot measurements are described separately in
[benchmarks/VALIDATION.md](../VALIDATION.md).
