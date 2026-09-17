# Selection evidence for ItaniumCXXABI::EmitThreadLocalInitFuncs

Source: [clang/lib/CodeGen/ItaniumCXXABI.cpp lines 3107-3309](https://github.com/llvm/llvm-project/blob/87f0227cb60147a26a1eeb4fb06e3b505e9c7261/clang/lib/CodeGen/ItaniumCXXABI.cpp#L3107-L3309). The snapshot is byte-for-byte from the pristine pinned commit and is licensed under LLVM's Apache-2.0 WITH LLVM-exception terms; see the collected license.

The `thread-local-init-ir` test invokes the corresponding `ir-generation` subsystem. The test uses structural sizes 4, 16, and 64, and its spec records the exact tool, flags, target path, and symbol. Specialized tool cases remain not-run where a harness is unavailable; host behavior is never treated as pinned marker coverage.

This region was selected because its implementation contains iteration over input-dependent compiler data, name or table lookup, AST or IR object construction. Those operations can scale with tokens, declarations, candidates, AST nodes, or IR objects depending on the caller. This is an opportunity hypothesis for profiling, not a ground-truth PCV assignment or a measured speedup.

Several-fold improvement is plausible only if measurement finds repeated scans, redundant lookup, avoidable rebuilding, or repeated diagnostics on growing inputs. The collection makes no claim that such behavior occurs for this function or supplied fixture.
