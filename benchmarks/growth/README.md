# Expansion to 1,000 cases

The starting collection contains 207 cases at commit `ee78644a3800a94bdeff3ab4bae1e2dd8665b0b6`. Three GPT-5.6 Sol agents collected 250 new cases each in compiler-frontends, language-tools, and general-libraries. The primary agent added 43 RapidJSON cases in native-libraries and handled integration and independent checks. Final total: 1,000.

A count is not a quality gate. Each collected region needs a full upstream commit and source hash, retained license, independent empty-marker patch, neutral task, separate evaluator notes, and a concrete target-specific workload with assertions. Generic syntax checks, random fallback arguments, or tests accepting any exception do not establish behavior. Host compiler results do not establish target-region entry. The compiler additions were verified using a pinned instrumented LLVM/Clang build.

All 793 additions are region-verified: 250 compiler cases passed assertions and exact native marker entry at sizes 4, 16, and 64; 250 language-tool and 250 general-library cases passed bounded Python assertions and marker probes; 43 RapidJSON cases passed compiled native observers and semantic assertions at five sizes. These are collected source targets, not 793 independent bugs or completed agent-evaluation trials.

`original-cases.json` records hashes for the original 207 case bundles and their snapshots. Run `python3 benchmarks/growth/audit.py` to verify those 1,089 files remain intact. Shared collection tools and new groups may change during expansion. The older `bench_anontated/audit.py` records the earlier whole-benchmark freeze and must be interpreted against its original commit, not silently rewritten to include this expansion.

Measured optimization evidence stays outside the baseline collection. The expanded escaped-cookie workload is in `bench_anontated/growth-multifold/aq-003` and `bench_optimized/growth-multifold/aq-003`: an already implemented optimization shows a 10.69x instruction reduction across the matrix, about 10x native function speedup at the largest 1,538-character input, and 66,045 matching differential checks. This is a concrete multifold example, not a completed drperf-versus-timing agent comparison.

The cookie small-to-larger experiment separately records numerical prediction error. A fit on inputs up to 290 characters predicts three fresh larger escaped-string sizes within 1.3% of total measured instructions, but misses the cheap control cases badly despite a low unexplained share. The annotation had prior exposure to other larger sizes, so this is a post-hoc exploratory split. It motivates reporting both unexplained-cost coverage and numerical error in the future agent benchmark; neither is a substitute for the other.

The separate vLLM queue experiment uses an FCFS incoming queue, a priority-queue
destination, and lightweight requests whose comparator is copied from the pinned
vLLM source. For an empty destination and a batch of at least 512 requests, a bounded descending-prefix check selects bulk heap construction.
On the measured descending batches of 512–1,000 requests, target instructions
fall 4.89–5.58x (5.34x weighted across those runs). Ascending and mixed controls
pay under 2% extra instructions. Both annotated and optimized models pass the
5% unexplained-share gate; their numerical reconstruction errors on the descending matrix
are below 2%. Eighty-four additional differential scenarios compare exact popped
object identities, including aliases, repeated objects, and identity ties. This
is an isolated queue-kernel result, not full vLLM inference throughput.

The [instruction comparison](performance-comparison.json) is recomputed by
`python3 benchmarks/growth/tools/compare_performance.py`. It requires matching
recorded states and call counts. Correctness and invocation/source audits live
beside each experiment. Failed annotation rounds and rejected surrogate queue
workloads are retained so they cannot silently become accepted evidence.

Final integrity and execution evidence:

- `receipt-integrity.json` checks all 793 saved receipts against current source,
  patch, and test assets. Compiler receipts bind executable hashes; general-library
  receipts also bind the actual marked module bytes executed in the runtime.
- `upstream-verification.json` compares every distinct new source snapshot with
  its pinned Git object. No source normalization is allowed.
- `compiler-build/entry-final/summary.json` records all 750 native compiler
  fixture executions. Development rounds remain separate.
- `language-tools-independent.json` records 16 independent reruns;
  `general-libraries-independent.json` records two seeded samples per project.
- `review/` records spot-review findings and the generator indentation repair.
  Those historical snapshots can differ from the final targets after repairs.

Recheck from the repository root:

```sh
python3 benchmarks/regions/collect.py check --require-tests
python3 benchmarks/growth/audit.py
python3 benchmarks/growth/tools/check_receipts.py --require-verified
python3 -m unittest discover -s benchmarks/tests -v
```

The fixtures seed investigation; they are not complete input domains or frozen
agent training/holdout splits. Keep source families together in future evaluation
splits. Low unexplained share, numerical prediction accuracy, correctness, and
measured improvement are separate evaluation quantities.
