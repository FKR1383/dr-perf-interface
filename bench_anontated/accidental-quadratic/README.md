# Accidental-quadratic annotation results

All 21 collected cases were exported here without modifying `benchmarks/`.
Each workspace retains its empty-marker source under `_baseline/`, its
annotation-only diff in `annotation.patch`, measurement artifacts under
`evidence/`, and a machine-readable `result.json`.

Nine annotations passed the strict DrPerf gate: `aq-003`, `aq-005`, `aq-006`,
`aq-008`, `aq-011`, `aq-012`, `aq-015`, `aq-018`, and `aq-019`. Ten reached
their regions with enough states but exceeded the 5% unexplained-instruction
limit. `aq-010` lacks a cheap entry-state value for recursive glob result
count. The `aq-009` full-checkout workload exercised Black's canonical module
rather than the separately loaded marked module, so it is recorded as a
workload failure. Every result points to the measurement matching its final
annotated source.

Annotation attempts were bounded to three valid DrPerf rounds. The retained
`round2` files with “no drperf files” document an attachment setup error and
are explicitly excluded from attempt counts; `round2b` is the corrected run.

Two optimizations were accepted after correctness, differential, and DrPerf
checks: `aq-003` reduces aggregate target instructions by 38.6%, and `aq-015`
by 13.8%. The `aq-008` candidate is rejected despite a 65.4% instruction
reduction because broader differential testing found behavior changes.

The other six qualified cases were reviewed individually. The two path
expanders require replacing a multi-syntax scanner, with broad str/bytes,
quoting, and environment semantics; moving a compiled replacement into module
globals would also shift work outside the region. The four email-parser cases
derive most of their work from shared helpers that return sliced remainder
strings. Removing those copies safely requires a cursor-style contract change
across functions outside each marked region. Their `result.json` files record
these case-specific reasons as `reviewed-no-safe-candidate`.
