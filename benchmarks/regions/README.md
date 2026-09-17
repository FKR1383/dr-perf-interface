# Collected source regions

Each case begins with no declared performance-critical variables. The human or
agent supplies those later. Upstream source and selection evidence are pinned
so a case is more concrete than a hotspot name or an unverified issue link.

```text
<group>/cases/<id>/case.json       identity, revision, region, empty marker
<group>/cases/<id>/region.patch    independent patch against upstream source
<group>/cases/<id>/task.md         neutral investigation task and trigger suggestion
<group>/cases/<id>/reference.md    historical findings / selection evidence
<group>/cases/<id>/tests/          bounded inputs and correctness assertions
<group>/test-support/             shared workload implementations, when needed
<group>/upstream/...              shared pristine source files and licenses
catalog.json                     index of collected cases, distinct from old inventory
support/drperf_bench_region.h     C++ scope-marker helper
```

Manifests give the original upstream path, full Git commit, snapshot SHA-256,
qualified symbol, and source line bounds. Shared snapshots avoid duplicating a
large source file for every target. Each patch applies to pristine source
independently; patches for different targets are alternatives, not a patch stack.
Line bounds refer to the pristine snapshot before adding imports or markers.

Python patches preserve the function docstring and introduce an empty context:

```python
import perfmark

with perfmark.region("case-id"):
    # original region body
    ...
```

C++ patches add the shared helper include and one scoped declaration:

```cpp
#include "drperf_bench_region.h"

void Function() {
  DRPERF_BENCH_REGION("case-id");
  // original region body
}
```

The helper calls `perfmark_begin_v(name, 0, nullptr, nullptr)` and balances it
with `perfmark_end` on scope exit, including early returns. It contains no PCV
expressions. Build the project's sources with `support/` and the repository's
`perfmark/` directory on the C++ include path, and link the PerfMark library.
Python needs the PerfMark Python binding and its native library. These source
patches do not configure V8's GN build or install project dependencies.

Use `collect.py export ID DESTINATION` to get the marked source, neutral task,
and declared tests and shared fixtures. Reference notes stay behind. The export
is not a complete upstream checkout. The isolated standard-library cases and native-library header workloads can
run directly with their stated interpreter or compiler; package-dependent cases need a full checkout at the recorded
revision with the case patch already applied and matching dependencies.

## Run a collected test

```sh
python3 benchmarks/regions/collect.py test aq-001
python3 benchmarks/regions/collect.py test v8-regexp-001 --d8 /path/to/patched/d8
python3 benchmarks/regions/collect.py test wan-001 \
  --python /path/to/venv/bin/python --source-root /path/to/patched/diffusers
```

The runner exports the test files and substitutes `{python}`, `{d8}`, and
`{source_root}` in the manifest's argument list. It does not install dependencies,
download models, or modify a supplied checkout. Without `--source-root`, it
uses the temporary export itself. A 120-second timeout is the default.

Tests contain small input generators and value/shape/error assertions, not
performance thresholds or PCV answers. Their `tests.validation.status` means:

| Status | Evidence |
| --- | --- |
| `not-run` | Concrete test exists; required dependencies, runtime, or target path has not been verified successfully. Details record failures or missing setup. |
| `behavior-checked` | Value assertions passed on the stated runtime; target marker entry remains unverified. |
| `region-verified` | Assertions passed and the intended marked source was entered. This is not proof of a cost model or speedup. |

Python workloads use `marker_probe.py` to observe entry and fail if the target
is missed. Native correctness runs replace only the marker with a recording
context; the target implementation runs unchanged. Under `DRPERF`, the observer
also forwards to the real PerfMark context. JavaScript behavior checks on Node
are explicitly separate from executing the pinned patched V8 shell. Unsupported
Unicode Sets tests fail rather than reporting a vacuous pass.

## Collection checks

```sh
python3 benchmarks/regions/collect.py check
python3 benchmarks/regions/collect.py check --require-tests
python3 benchmarks/regions/collect.py index
python3 -m unittest discover -s benchmarks/tests -v
```

The checker verifies byte hashes, full revision pins, line bounds, independently
applicable patches, one touched source file, one empty marker, and unique exact
source targets. Python patches must restore the pristine AST when the marker
and added import are removed. C++ patches may only add the helper include and
one macro invocation. The native-library slice compiles pinned RapidJSON headers
and checks the target observer. Full V8/LLVM instrumented builds remain separate
from those checks. A standalone helper test checks zero PCVs and balanced
entry/exit on an early return.

These checks are collection integrity checks, not performance validation.
Declared test assets, shared-resource hashes, and commands are checked too.
Having a test file is separate from successfully verifying its target entry.
Marking a V8 runtime function does not guarantee a JavaScript workload takes
that fallback, and marking a bytecode generator measures compilation work.
The RegExp parser/compiler/execution phases are likewise distinguished.

The historical vLLM and Wan conversion can be reproduced with:

```sh
python3 benchmarks/tools/collect_archived_regions.py /home/ubuntu/drperf-cases
```

It uses marked archive copies to locate candidate functions and blocks, but
exports their source from pristine pinned Git commits and removes all proposed
PCVs. Matching child blocks and whole functions share `source_family`; preserve
those groups in later evaluation splits. Accidental-quadratic regions are
linked to upstream reports and fixes, including multiple affected functions
within one report. Do not describe all source targets as independent defects.
