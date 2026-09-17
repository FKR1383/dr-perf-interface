# Escaped-cookie workload: measured multifold reduction

This extends the workload for the existing `aq-003` optimization, which replaces two repeated regex suffix searches with one combined escape substitution. It is not a new blinded agent discovery. The original benchmark and earlier experiments are unchanged.

The new valid input family repeats `a\"` inside a quoted cookie. The old code searches for an octal escape in the remaining suffix on every iteration, although none exists. Input sizes are 50, 98, 194, 386, 770 and 1,538 characters, plus `None` and `plain` controls. Both implementations receive identical tests.

The first annotation (`input_len`, `input_pairs`) failed the 5% maximum unexplained-share gate at 8.81%. Adding an explicit quoted-input branch indicator and an expression for indices beyond CPython's small-integer cache reduced the maximum to 3.73%. This fourth PCV is specific to the three-character repeating workload; it is not a general cookie cost formula. The optimized version passes with 0% unexplained cost on the observed states.

Measured target instructions fall from 29,105,026 to 2,723,101 across the matrix: 10.69x. At 1,538 characters the instruction ratio is 14.97x. Native function timing at that state is 10.03x faster in this run; timing includes identical no-op Python marker contexts and PCV computation. It excludes process startup and is not end-to-end HTTP throughput. Concurrent collection work may affect timing.

`validate.py` performs 66,045 differential comparisons (exhaustive short strings, seeded random strings, controls, and repeated escape families) and 11 alternating native timing rounds at each size. No differences were found. `evidence/validation.json` stores hashes and timing samples; `result.json` links the real drperf measurements. These are observations, not a proof for untested inputs.

Reproduce from repository root:

```
python3 bench_optimized/growth-multifold/aq-003/validate.py
python3 bench_anontated/measure.py run --case aq-003 --workspace bench_anontated/growth-multifold/aq-003 --out /tmp/cookie-before-new -- python3 tests/test_case.py --source-root "$PWD/bench_anontated/growth-multifold/aq-003"
python3 bench_anontated/measure.py run --case aq-003 --workspace bench_optimized/growth-multifold/aq-003 --out /tmp/cookie-after-new -- python3 tests/test_case.py --source-root "$PWD/bench_optimized/growth-multifold/aq-003"
```

A separate post-hoc small-to-larger split fits only inputs up to 290 characters, then checks new 482-, 962-, and 1,922-character inputs without refitting. The accepted affine component underpredicts their total counts by 1.24%, 0.97%, and 0.74%. This is exploratory: the annotation had already been developed using other sizes up to 1,538 characters. It is not a blinded prospective prediction.

This also exposed a useful benchmark distinction: low unexplained share does not bound the aggregate formula's numerical error. The `None` and `plain` controls have large formula errors even though the training unexplained-share gate passes. Per-block absolute tolerances accumulate, and the current derivation folds small slopes into constants. `check_predictions.py` in the annotated workspace records every training and holdout row in `evidence/small-to-larger.json`, including those failures. Future evaluation should report numerical prediction error separately from unexplained-cost coverage.

The same reconstruction check on the main before/after matrix also finds large formula errors on cheap controls (up to 412% before and 103% after), despite both unexplained-share gates passing. `formula-reconstruction.json` retains every row. The measured instruction reductions and correctness results remain valid; the gate should not be described as a 5% prediction-accuracy guarantee.
