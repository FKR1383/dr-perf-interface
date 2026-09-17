# DeclContext::lookupImpl

Inspect the empty marked function in `clang/lib/AST/DeclBase.cpp` at LLVM commit `87f0227cb60147a26a1eeb4fb06e3b505e9c7261`. Identify runtime state that explains its cost without changing compiler behavior.

Use the supplied `ast-dump` workload at structural sizes 4, 16, and 64. Run it with the explicit tool and flags in `tests/spec.json`, preserving the assertions at every size when investigating scaling. The marker begins with no PCVs.

For region-entry measurement, apply `region.patch` independently to a full checkout, configure LLVM with `-DLLVM_ENABLE_PROJECTS='clang;clang-tools-extra'`, add the collection support and PerfMark include paths, link PerfMark, and run the newly built tool. See the group README for exact setup commands.
