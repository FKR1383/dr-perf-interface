# zlib compression case study

Run the variable-discovery evaluation on the real zlib 1.3.1 C implementation.
A small driver calls zlib and verifies every compressed buffer by decompressing
it and comparing the original bytes. The `compress` region covers compression;
file loading, allocation, stream initialization, and verification are outside it.

The [first-run report](RESULTS.md) records the observed answers and limitations.

## Prepare

Build Dr. Perf with `./build.sh` first. From the repository root:

```sh
python3 evaluation/case_studies/zlib/prepare.py
```

This downloads the pinned zlib archive, verifies its SHA-256 checksum, copies
the source and marker library into `build/evaluation-zlib`, compiles the driver,
and checks all 96 discovery cases. To use a downloaded archive, pass
`--archive /path/to/zlib-1.3.1.tar.gz`. Existing destination directories are
rejected; choose new paths with `--workspace` and `--validation-dir` to prepare
another copy.

The case-study author fixes the workload values before evaluation. The agents
choose variables and expressions; they cannot change the inputs between attempts.

| Input dimension | Discovery | Reserved validation |
| --- | --- | --- |
| Buffer sizes (KiB) | 1, 4, 16, 32, 48, 64 | 2, 8, 24, 40, 56, 72 |
| Compression levels | 1, 3, 4, 6 | 1, 3, 4, 6 |
| Source and text | Prefixes of zlib's deflate.c and ChangeLog | Slices starting 4 KiB later |
| Repetitive control | Repeating abcd | Repeating 0123456789abcdef |
| Random control | Deterministic discovery seed | Different deterministic seed |

Both workloads have 96 calls. Validation files and the provenance record live
in `build/evaluation-zlib-validation`, outside the agent workspace. The source
and text slices overlap the discovery material: this checks new lengths and
offsets, not generalization to an entirely independent document corpus.

## Run the agents

An authenticated `codex` executable must be on PATH.

```sh
python3 evaluation/run.py \
  --workspace build/evaluation-zlib \
  --region compress \
  --max-attempts 10 \
  --target-irregularity 0.10 \
  --results-dir evaluation/results/zlib-discovery \
  -- ./program workloads/discovery.tsv
```

The result directory must be new or empty. Full zlib source is available to both
agents. No candidate features or expected answers are supplied to them. The
original marker records `n`; the experimental agent can replace its declaration.
The agent keeps experimenting until irregularity is below 10% or all ten
attempts are used. An unmet target is saved and reported with exit code 2.

## Check the selected answers

Review `result.json` and the agent logs first. Then:

```sh
python3 evaluation/case_studies/zlib/validate.py \
  --results evaluation/results/zlib-discovery/result.json \
  --out evaluation/results/zlib-validation
```

This creates disposable copies, instruments each agent's selected expressions
at the original boundary, rebuilds, and measures both workloads. It supplies no
feedback to either agent and checks that the frozen workload files are unchanged.
If an answer needs unavailable bindings, non-integer values, or more than four
states, validation reports the limitation rather than substituting different
features. In particular, the pointer `input` does not summarize the buffer's
contents; casting its address to an integer would not measure that dependency.

`validation.json` contains discovery and validation irregularity for each answer.
Validation irregularity uses newly fitted coefficients with the selected features
held fixed. A separate prediction check fits a full-precision formula on a replay
of discovery, freezes it, and compares it with validation mean instruction counts. Gaps between
discovered regimes are left unpredicted. Prediction error includes cost that the
discovery formula classified as irregular, since that cost is absent from its
prediction.

Dr. Perf averages calls with identical declared state values. For example, a
model declaring only `n` averages across levels and contents at each length.
Low irregularity therefore does not establish accurate predictions for every
individual file. Neither a zero-irregularity result nor a missed feature is
assumed in advance; unsuccessful discovery runs are useful evidence too.

The scripts add instrumentation only; they do not modify the zlib algorithms.
The downloaded source retains its upstream license in `zlib/README`.
