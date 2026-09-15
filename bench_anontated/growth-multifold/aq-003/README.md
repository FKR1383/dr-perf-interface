# Annotated escaped-cookie workload

Baseline source copied from the existing annotated `aq-003`, with a new quote-only repeated-escape test matrix and an additional annotation round driven by drperf feedback. The original benchmark remains unchanged.

`evidence/round1` retains the failed two-PCV annotation result (8.81% maximum unexplained share). `evidence/round2` records the accepted four-PCV annotation (3.73%). See `../../../bench_optimized/growth-multifold/aq-003/README.md` for the optimization, correctness checks, measurement limits, and reproduction commands.
