## A third-party library: pricing a quadratic in sqlglot's optimizer, and declining to fix it

The previous cases all ended in a fix. This one ends in a number and a refusal,
which is the other thing a cost function is for: deciding that a change is not
worth making, or not yours to make.

**Finding the target.** `oss/screen.py` and `oss/screen2.py` run eleven
workloads across sqlglot, networkx, Pygments, markdown-it-py, mistune,
jsonschema, docutils and Jinja2 at n, 2n and 4n and report the doubling ratio.
Ten of the eleven are flat at 1.7x to 2.0x. One is not:

```
sqlglot.optimize_n_joins   60   294.39ms   937.55ms  3409.01ms   3.18x 3.64x  <== SUPERLINEAR
```

**The fit.** One region around one `sqlglot.optimizer.optimize` call, states the
join count and its square, swept from 10 to 80 joins:

```
cost(n_joins, n_joins_sq) = 10,950,467.9*n_joins + 484,257*n_joins_sq
                          + 87,961,347.4
    blocks: 6699 affine, 9954 constant, 979 irregular   (1.7% of cost)
```

**The formula extrapolates.** Fitted on 10 to 80 joins, it was then checked at
sizes it never saw:

| joins | predicted | measured | error |
|---|---|---|---|
| 160 | 14,237,015,411 | 14,372,870,280 | +0.9% |
| 240 | 30,609,276,843 | 30,787,546,646 | +0.6% |

A threefold extrapolation to under one percent. It also states the crossover:
the quadratic term passes the linear one at 10,950,467 / 484,257 = **23 joins**,
so below that the optimizer is effectively linear and above it it is not.

**Where it comes from.** Attributing the walked nodes inside `Scope._collect` to
the optimizer rule that triggered them, at 160 joins:

| rule | nodes walked | share |
|---|---|---|
| `merge_subqueries.py` | 1,131,034 | **96.2%** |
| `qualify.py` | 11,659 | 1.0% |
| everything else, seven rules | 33,000 | 2.8% |

And the mechanism is a round trip. `optimize()` sets `isolate_tables=True`,
"needed for other optimizations to perform well", so `isolate_table_selects`
wraps every one of the N joined tables in its own single-use CTE. `merge_ctes`
then merges all N of them back. Each merge calls `_merge_from`, which mutates
the AST and so must invalidate the outer scope's analysis, and then
`_merge_expressions`, which reads `outer_scope.columns` and pays a fresh full
walk of an expression that is itself O(N). N merges times an O(N) walk is the
`n_joins_sq` term. Counted directly:

| joins | query nodes | full re-collects | nodes walked |
|---|---|---|---|
| 40 | 395 | 372 | 82,651 |
| 80 | 795 | 732 | 306,171 |
| 160 | 1,595 | 1,452 | 1,175,611 |

The re-collect count grows linearly and the work grows as the square.

**Why I did not fix it.** The invalidation is not a stray bug: `_merge_from`
really does rewrite the tree before `_merge_expressions` reads it, so the cache
really is stale. Removing the quadratic means maintaining the scope's column
index incrementally across six merge helpers, each of which splices inner
expressions into the outer query. The obvious shortcut, computing the
alias-to-columns map once before the loop, is correct for the isolated-table
pattern that produces this workload and wrong in general, because a CTE may
select from another CTE that is merged later. That is a redesign of a widely
used SQL optimizer on the strength of a plausibility argument, and it belongs to
the maintainers.

**What is available without a fix.** Dropping the one rule is a supported
option, `optimize(..., rules=...)`, and it is worth measuring rather than
guessing:

| joins | all 14 rules | without `merge_subqueries` | speedup |
|---|---|---|---|
| 40 | 150 ms | 69 ms | 2.2x |
| 80 | 464 ms | 140 ms | 3.3x |
| 160 | 1,553 ms | 322 ms | 4.8x |
| 240 | 3,392 ms | 497 ms | 6.8x |

The output is not the same: without the rule the N single-use CTEs survive into
the emitted SQL, which is valid but verbose. So this is a real trade, and the
formula is what lets someone price it: below 23 joins there is nothing to buy,
and at 240 joins it is most of the runtime.

**The baseline for anyone who does attempt it.** The upstream repository at
v30.18.0 was cloned and its suite run as a reference point: 1,245 tests and
19,422 subtests pass, with one unrelated environment failure
(`test_lazy_load`, a missing file). Any fix has that to clear.

**What this case adds.** The three cases before it show a cost function finding
work to remove. This one shows it doing the other half of the job: quantifying a
cost precisely enough to extrapolate threefold within one percent, attributing
96% of it to a single rule, and then supporting the decision *not* to change the
code, plus a measured price for the workaround that exists today. A profile of
one query would have shown time in `walk_in_scope` and none of that.

