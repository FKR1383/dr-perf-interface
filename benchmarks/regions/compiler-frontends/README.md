# Compiler front-end regions

This group collects distinct native functions from LLVM/Clang 20.1.8 across
lexing, parsing, semantic analysis, AST processing, diagnostics, serialization,
source tooling, IR generation, IR parsing, and IR construction.

Each fixture is deliberately bounded and checks compiler behavior using explicit
flags. Native entry validation applies the independent patch to the pinned LLVM
checkout, builds that checkout with the observer helper, and requires the exact
marker at each of the three fixture sizes.

The reference notes describe structural reasons a region may be worth profiling.
They are hypotheses rather than answer keys or speedup claims.

## Reproduce the behavior checks

The general Clang scenarios use the compiler named by `DRPERF_CC`, or `clang`
when that variable is unset. They exercise three structural sizes per case.

```sh
python3 benchmarks/regions/collect.py test cf-001
```

The formatting checks were run with the release-matched PyPI binary:

```sh
python3 -m venv /tmp/drperf-cf-tools
/tmp/drperf-cf-tools/bin/pip install clang-format==20.1.8
DRPERF_CC=/tmp/drperf-cf-tools/bin/clang-format \
  python3 benchmarks/regions/collect.py test cf-142
```

The remaining specialized tools are built from the pinned LLVM checkout. A
minimal tools build uses these exact commands (Ninja and a C++ compiler are
prerequisites):

```sh
git clone https://github.com/llvm/llvm-project.git /tmp/llvm-project-20.1.8
git -C /tmp/llvm-project-20.1.8 checkout 87f0227cb60147a26a1eeb4fb06e3b505e9c7261
cmake -S /tmp/llvm-project-20.1.8/llvm -B /tmp/llvm-project-20.1.8-build \
  -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_ENABLE_PROJECTS='clang;clang-tools-extra' \
  -DCLANG_ENABLE_STATIC_ANALYZER=ON -DCLANG_ENABLE_ARCMT=OFF
cmake --build /tmp/llvm-project-20.1.8-build --target \
  clang clang-check clang-scan-deps clang-import-test
```

Set `DRPERF_CC` to the required binary in that build's `bin/` directory when
running a specialized case. The collected suite was checked with the pinned
`clang`, `clang-format`, `clang-check`, `clang-scan-deps`, and
`clang-import-test` binaries. LLVM 20.1.8 has no `clang-syntax-test`
command-line target; coverage-guided target selection avoids claiming that a
fictional binary runs the Syntax tree library.

To verify native entry, apply each case patch independently (or insert all
markers in a dedicated coverage checkout), include `support/` and PerfMark's
headers, link PerfMark, and run the pinned tool. Host behavior checks alone do
not establish that the pinned marked function was entered.

The hash-bound observer receipts are stored in
[`../../growth/compiler-build/entry-final/`](../../growth/compiler-build/entry-final/).
They record the pinned revision, pristine source identity, region bounds, patch,
test assets, instrumented binary, return code, and marker count for every size.
`tools/promote_validation.py` checks all of those bindings before changing any
manifest to `region-verified`. Marker entry proves reachability only; it is not
a cost measurement or a speedup result.
