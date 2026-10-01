# wan-025: full-feedback evaluation

This directory is the human-readable record. Trusted controller state is kept
separately under `../.controller-runs/wan-025`.

1. `case-actual/` — fixed clean case export; `src/diffusers/pipelines/wan/pipeline_wan.py` has an empty marker.
2. `iterations/iteration-NNN/annotation.diff` — only the annotation change.
3. `iterations/iteration-NNN/drperf-full-report.json` — complete Dr. Perf metrics.
4. `case-report.json` and `case-report.md` — complete per-case result.
5. `../full-report.*` — complete benchmark result.
6. `agent_PCVs/PROMPT.md` — common selector instructions used for every benchmark.
7. `agent_PCVs/isolation.json` — isolation and persistent-thread receipt.
8. `iterations/*/script-decision.json` — deterministic black-box controller result.

The workload is immutable across iterations. Exact PCV names and expressions
are recorded in each iteration directory and in the case report.
