# Wan annotation results

All 41 Wan cases were exported independently from the pinned Diffusers snapshots and annotated with one cheap entry-state PCV. Their original correctness tests pass against isolated full source trees.

After the feedback refinement pass, eighteen cases passed the strict annotation gate. Twenty-three completed measurement but did not qualify, principally because the unsplit affine model left more than 5% of instructions unexplained; each case's `result.json` retains the exact metrics and reason. No unqualified case advanced to optimization.

The blend cases use positive extents 1, 2, and 3 for the final gated performance workload. Separate edge tests cover extents -1 and 0, aliasing, and float64, float32, float16, and bfloat16. Their numeric comparisons use matching relative and absolute tolerances of 1e-12, 1e-6, 1e-3, and 1e-2 respectively.

[REFINEMENT.md](REFINEMENT.md) records the additional feedback reviews and thirteen second measurements that produced two more qualifying annotations.
