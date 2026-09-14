## libcst: three left-recursive grammar rules, and a 102x parse

**Target.** `libcst` 1.9.0, Meta's concrete syntax tree library for Python. It is the
parser behind large-scale codemods and behind tools that read Python source, so its
parse time is on the critical path of anything that touches a whole repository.

### Finding it

Eleven workloads across eight libraries were screened at n, 2n and 4n
(`oss/screen.py`, `screen2.py`, `screen3.py`, `screen4.py`). Ten were flat. The
interesting comparison was against CPython's own parser on the same input:

| shape, 4x input | libcst | CPython `ast` |
|---|---|---|
| `a + b + c ...` | **9.4x** | 3.8x |
| `a \| b \| c ...` (type union) | **9.7x** | 4.5x |
| `obj.m0().m1()...` (method chain) | **19.2x** | 5.8x |
| `a.b.c.d ...` (attribute chain) | **10.5x** | 3.4x |
| `[a0, a1, ...]` (flat list) | 3.8x | 4.0x |

Flat structures are fine. Everything deeply *left-nested* is quadratic, and CPython
parses the identical text in linear time, so it is not inherent to parsing Python.

### Beat one, the fit

```
$ drperf run --blocks --repeat 2 --state n_terms=50,100,...,300 \
      -o out/libcst_fit -- python oss/run_libcst.py shape=0

cost(n_terms, n_terms_sq) = 122,714.4*n_terms + 1,034.9*n_terms_sq + 2,100,550.4
    blocks: 2958 affine, 12742 constant, 496 irregular   (3.7% of cost)
```

### Beat two, the surprise

A Python profiler cannot see into this: `cProfile` reports 0.026 s of 0.031 s inside
`entrypoints.py:_parse`, a single native call, and stops. drperf attributes the
*quadratic term alone*, by function, across the language boundary:

```
per-n_terms_sq coefficient by function:
     300    _int_free                                        [libc]
     181    <DeflatedExpression as core::clone::Clone>::clone [libcst_native]
     181    __GI___libc_malloc
     124    __free
      71    drop_glue::<DeflatedExpression>                  [libcst_native]
```

The quadratic is a `clone` of the expression built so far, plus the allocator traffic
it causes. The cause is in the grammar:

```rust
#[cache_left_rec]
rule sum() -> Expression
    = a:sum() op:lit("+") b:term() {? make_binary_op(a, op, b) }
    / a:sum() op:lit("-") b:term() {? make_binary_op(a, op, b) }
    / term()
```

`rust-peg` implements left recursion by seed growing: the rule body is re-evaluated
once per operator in the chain, and each growth stores the partial result in the rule
cache, which clones it. Clone of a chain of depth k is O(k), so n operators cost
O(n^2). Nine rules are written this way.

### Beat three, the fix

The textbook transformation, `X = X op Y / Y` becomes `X = Y (op Y)*` folded left,
which builds the identical tree because the fold is left-associative:

```rust
#[cache]
rule sum() -> Expression
    = a:term() rest:(op:(lit("+") / lit("-")) b:term() { (op, b) })* {?
        rest.into_iter().try_fold(a, |acc, (op, b)| make_binary_op(acc, op, b))
    }
```

Applied to three families: the six binary-operator rules, `primary` (attribute, call,
genexp-call and subscript suffixes, folded through a small `PrimaryTail` enum), and
`t_primary`, the same chain grammar used for assignment targets. `t_primary` matters
because a bare `obj.m0().m1()...` statement is first *tried* as an assignment target,
so the chain was parsed quadratically once before the parser backtracked and read it
as an expression.

### The same formula, re-derived after the fix

| shape | stock `n_terms_sq` | fixed `n_terms_sq` |
|---|---|---|
| `a + b + c ...` | 1,034.9 | **-0.134** |
| `obj.m0().m1()...` | 8,458.1 | **0.639** |

The quadratic term is gone, not merely reduced.

### Results

Parse time for a single expression, and the doubling ratio:

| chain length | stock | fixed |
|---|---|---|
| 100 | 14.8 ms | 2.8 ms |
| 200 | 55.6 ms (3.8x) | 5.9 ms (2.1x) |
| 400 | 235.0 ms (4.2x) | 10.7 ms (1.8x) |
| 800 | 1,045.9 ms (4.5x) | 21.8 ms (2.0x) |
| 1,600 | 4,505.3 ms (4.3x) | 44.2 ms (2.0x) |

**102x at 1,600 links**, and the scaling is linear rather than quadratic.

At 800 terms, by shape:

| shape | stock | fixed | speedup |
|---|---|---|---|
| `obj.m0().m1()...` | 1,808.4 ms | 45.0 ms | **40.2x** |
| `a.b.c ...` | 232.9 ms | 17.5 ms | 13.3x |
| `a \| b \| c ...` | 214.3 ms | 24.7 ms | 8.7x |
| `a + b + c ...` | 173.5 ms | 26.0 ms | 6.7x |

And on ordinary real-world Python, 562 files and 7 MB from three unrelated projects
(sqlglot, libcst itself, spec2lean):

| | stock | fixed |
|---|---|---|
| parse whole corpus | 14.560 s | 11.912 s |

**18.2% off real parsing**, with no pathological input anywhere in the corpus.

### Correctness

- **Upstream test suite**: 1,160 passed, 11 skipped, 72 subtests passed. Identical
  to the stock build's result on the same command.
- **Structural equality on real code**: all 562 corpus files parsed with both builds
  and digested with `repr(module)`, libcst's full structural representation. Corpus
  digest `a979ad1387f6b9b5` on both. Not merely equal source after round-tripping,
  the same tree.
- **Round-trip**: 562 of 562 files satisfy `parse_module(src).code == src` on both.

### Reproducing

```bash
git clone --depth 1 --branch v1.9.0 https://github.com/Instagram/LibCST oss/libcst-src
cp -r oss/libcst-src oss/libcst-fix4
python oss/fix_libcst.py oss/libcst-fix4 --primary --t-primary
cd oss/libcst-fix4/native && cargo build --release          # 24 s
cp target/release/liblibcst_native.so ../libcst/native.cpython-312-x86_64-linux-gnu.so
python -m pytest libcst/tests libcst/_nodes/tests -q --ignore=libcst/tests/test_fuzz.py
```

The patch is `libcst_fixes.patch`; the equivalence checker is `oss/equiv_libcst.py`
and the corpus timer is `oss/bench_corpus.py`.

### Why this is the case the others were not

The cold-start case was found with a profiler and drperf only sized it. This one a
Python profiler cannot reach at all: the entire cost is one opaque native call. drperf
counted instructions across the language boundary, separated the linear term from the
quadratic one, and attributed the quadratic *specifically* to `DeflatedExpression::clone`
inside the Rust extension. That named the grammar construct, the construct named the
transformation, and the transformation is worth 102x on a chain, 18.2% on ordinary
code, and provably the same syntax tree.


