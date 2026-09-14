# Accidental quadratic regions

This collection contains 21 Python source regions pinned to pre-fix upstream
revisions. The older revisions preserve the reported behavior while keeping
the region patch limited to an empty `perfmark.region(...)` marker. No upstream
fix is included in a case patch.

## Source groups

| Cases | Project and evidence family | Regions |
| --- | --- | ---: |
| `aq-001` | CPython enum creation, issue 89580 | 1 |
| `aq-002` | Cython type hierarchy ordering, PR 5139 | 1 |
| `aq-003` | CPython cookie decoding, issue 123067 | 1 |
| `aq-004` | CPython HTML parsing, issue 135462 | 1 |
| `aq-005`–`aq-006` | CPython path expansion, issue 136065 | 2 |
| `aq-007`, `aq-011`–`aq-021` | CPython email parsing, issue 136063 | 12 |
| `aq-008` | CPython CSV dialect detection, issue 98820 | 1 |
| `aq-009` | Black parenthesis normalization, PR 5322 | 1 |
| `aq-010` | Socket CLI file discovery, PR 22 | 1 |

The 11 cases `aq-011` through `aq-021` are separate functions explicitly
enumerated by the same CPython email security issue. They share one pristine
source snapshot and one evidence family. Evaluations should account for that
relationship rather than treating them as 11 independent upstream reports.

Each manifest records the full source revision and SHA-256 digest. Its
`source_family` identifies the upstream issue or project/function family used
to group related cases. Pristine sources and the license in effect at each
pinned revision are stored below `upstream/`.

Every patch adds one plain `import perfmark` and one empty Python context
marker with no PCV parameters. The patches apply independently and restore to
the pristine source AST when the marker and import are removed.

These are collection-only cases. Their `build_status` is `not-built`, and
their workload commands are `null`. The bounded trigger descriptions are
derived from upstream reports, but this collection does not guarantee that a
region is reachable in the local environment or that quadratic scaling has
been reproduced or measured here.

Each case also includes a bounded correctness workload in `tests/test_case.py`.
The workload loads the exported source path, checks a concrete result or error,
and uses the shared marker probe to verify region entry while forwarding to the
real marker when run under DrPerf. Native checks verified region entry for all
21 cases with Python 3.12. Cython, Black, and Socket CLI were checked against
isolated pinned full checkouts because a single-file export does not contain
their package trees; their case-local test READMEs record the setup. These
tests establish correctness and marker reachability only; they do not
establish a complexity class.
