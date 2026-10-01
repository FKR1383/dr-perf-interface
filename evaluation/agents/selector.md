# Agent 1 — PCV selector

Start this agent as a fresh session with only the generated `<run>/selector/`
directory visible. Its generated `PROMPT.md` is the authoritative prompt.

The selector may inspect source and run native correctness checks. It annotates
the existing region and fills in `workspace/CANDIDATE.json`. It must never have
access to Dr. Perf, DynamoRIO, prior annotations, full measurement output, the
repository's `bench_anontated` results, or another run. After a failed valid
attempt, it receives only the worst irregularity percentage.

The same session may be continued between iterations. If the agent system does
not support continuation, the retained workspace, prompt, and redacted
`feedback.json` provide the complete allowed history.

