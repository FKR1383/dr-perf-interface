# Wan unqualified-case refinement

This bounded follow-up reviewed 25 first-round, unqualified cases. It retained second measurements for 13 representative cases and kept the original measured annotation for 12 cases whose credible models require a redesigned multi-axis workload. Every final source therefore has a matching `final_measurement`.

Two refinements passed the strict affine 5% gate: `wan-021` uses patch-grid token count (2.39% maximum unexplained share), and `wan-026` uses denoising-loop iteration index (4.16%). Both received an optimization review; neither had a safe local candidate because the first is coupled to cached rotary-frequency layout and the second contains stateful scheduler/model iteration semantics.

The other retained second runs failed the gate: `wan-004`, `wan-005`, `wan-006`, `wan-016`, `wan-024`, `wan-031`, `wan-032`, `wan-033`, `wan-034`, `wan-036`, and `wan-040`. Their result files preserve the measured residuals. `wan-016`, `wan-033`, and `wan-036` were closest at 6.31%, 7.44%, and 7.78%. The run budget was capped at 60 seconds per process and two total annotation attempts for this follow-up.

The remaining result files record the concrete source-level reason a forced one-scalar refinement was not retained, including internal chunking, independent temporal/spatial tiling axes, mixed self/cross-attention regimes, and prompt batch/content confounding.
