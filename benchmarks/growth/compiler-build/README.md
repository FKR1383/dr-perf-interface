# Pinned compiler entry validation

LLVM/Clang 20.1.8 was built at commit
`87f0227cb60147a26a1eeb4fb06e3b505e9c7261` to check whether each compiler fixture
enters its selected source region. `instrumented.json` records the source files
with all 250 markers inserted from the independent case patches.

Simultaneous markers are for native reachability only. They must not be used to
report drperf costs: nested regions affect attribution. Normal case exports
retain one independent empty marker.

The observer records region names to `DRPERF_ENTRY_LOG`. It records no PCVs,
instruction counts, or timing. Each fixture size runs in a separate process;
a passing case requires its output assertions and its named target entry at
every size. The final entry report binds results to source identity, region,
patch, test assets, instrumented source record, and executable hashes.

## Reproduce the native check

Use a dedicated worktree of the pinned LLVM repository with `clang`, `llvm`,
`clang-tools-extra`, `cmake`, and `third-party` available. The local validation
used Clang 18.1.3, Ninja, a Release build with LLVM assertions, and X86 support.
The paths below are disposable build paths, not repository dependencies.

```sh
mkdir -p /tmp/drperf-growth-llvm-probe
clang++ -std=c++11 -shared -fPIC -O2 benchmarks/growth/tools/compiler_observer.cpp -o /tmp/drperf-growth-llvm-probe/libperfmark.so
python3 benchmarks/growth/tools/prepare_compiler_probe.py /tmp/drperf-growth-llvm-buildsrc --record benchmarks/growth/compiler-build/instrumented.json
cmake -S /tmp/drperf-growth-llvm-buildsrc/llvm -B /tmp/drperf-growth-llvm-build -G Ninja -DCMAKE_MAKE_PROGRAM=/usr/bin/ninja -DLLVM_ENABLE_PROJECTS='clang;clang-tools-extra' -DLLVM_TARGETS_TO_BUILD=X86 -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE='-O2 -DNDEBUG' -DCMAKE_C_FLAGS_RELEASE='-O2 -DNDEBUG' -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_ZLIB=OFF -DLLVM_PARALLEL_LINK_JOBS=2 -DLLVM_ENABLE_ASSERTIONS=ON -DCMAKE_CXX_FLAGS="-I$PWD/benchmarks/regions/support -I$PWD/perfmark" -DCMAKE_EXE_LINKER_FLAGS='-Wl,--no-as-needed /tmp/drperf-growth-llvm-probe/libperfmark.so -Wl,-rpath,/tmp/drperf-growth-llvm-probe'
/usr/bin/ninja -C /tmp/drperf-growth-llvm-build -j32 clang clang-format clang-check clang-scan-deps clang-import-test
python3 benchmarks/growth/tools/check_compiler_entries.py --bin /tmp/drperf-growth-llvm-build/bin --record benchmarks/growth/compiler-build/instrumented.json --out benchmarks/growth/compiler-build/entry-final
```

Rebuild after changing the marker overlay. An old successful build does not
validate new marker locations. `entry-results`, `entry-round2`, and `entry-round3`
are development evidence for earlier target/fixture assignments; they do not
certify the final case with a reused ID.

## Coverage-guided fixture repair

The first native checks exposed many fixtures that exercised a subsystem but
missed their named target. A separate coverage build used
`-fprofile-instr-generate -fcoverage-mapping` in both C and C++ flags, with `-O1`
and a matching Clang 18 profile runtime. Set `LLVM_PROFILE_FILE=/dev/null` while
building so build tools do not leave profiles in the checkout.

`benchmarks/growth/tools/collect_compiler_coverage.py` runs bounded fixtures, merges their process
profiles with `llvm-profdata`, and exports covered functions using `llvm-cov`.
It translates marked source coordinates back to pristine lines. A partial sweep
of 24 fixtures plus a formatter fixture supplied enough reachable functions to
replace the missed targets; exporting all 250 large compiler profiles was
unnecessary. Per-size marker checks validate the replacements separately:
merged source coverage alone cannot establish entry at every size.

The compiler collection retains replacement selection and witness provenance in
`benchmarks/regions/compiler-frontends/tools/`. Selection favors substantial
function bodies across compiler phases, and excludes duplicate exact regions.
Function entry still does not imply every branch or loop in that function ran;
these are bounded collection workloads, not exhaustive path coverage.
