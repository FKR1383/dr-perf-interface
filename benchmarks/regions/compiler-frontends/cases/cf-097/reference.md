# Selection evidence for Sema::ActOnNumericConstant

Source: [clang/lib/Sema/SemaExpr.cpp lines 3672-4107](https://github.com/llvm/llvm-project/blob/87f0227cb60147a26a1eeb4fb06e3b505e9c7261/clang/lib/Sema/SemaExpr.cpp#L3672-L4107). The snapshot is byte-for-byte from the pristine pinned commit and is licensed under LLVM's Apache-2.0 WITH LLVM-exception terms; see the collected license.

Pinned source coverage observed this function during the combined `control-flow-graph` witness run from static-analysis work; per-size native entry is checked separately. The test uses structural sizes 4, 16, and 64, and its spec records the exact tool, flags, target path, and symbol. Specialized tool cases remain not-run where a harness is unavailable; host behavior is never treated as pinned marker coverage.

This region was selected because its implementation contains iteration over input-dependent compiler data, name or table lookup, token consumption or parsing. Those operations can scale with tokens, declarations, candidates, AST nodes, or IR objects depending on the caller. This is an opportunity hypothesis for profiling, not a ground-truth PCV assignment or a measured speedup.

Several-fold improvement is plausible only if measurement finds repeated scans, redundant lookup, avoidable rebuilding, or repeated diagnostics on growing inputs. The collection makes no claim that such behavior occurs for this function or supplied fixture.
