## A second codebase, written by an agent: a 111x faster tree walk in spec2lean

`spec2lean` is a specification-to-Lean pipeline whose git history is 70 of 170
commits authored by a coding agent. Phase 1 turns a PDF or HTML specification
into a hierarchical SQLite index; the read-only query commands over that index
are deterministic, offline and pure CPU, which makes them a clean drperf target.
Three prebuilt indexes ship with the repository, of 504, 10,684 and 24,352
nodes, so document size is a state that can be varied without building anything.

The first timing pass over the read-only commands is the reason to look:

```
index stats        0.13 s      index definitions  0.12 s
index xrefs        0.12 s      index dump         0.11 s
index tree        71.80 s      index validate    73.66 s
```

Seventy-one seconds to print a heading hierarchy of 1,400 lines.

**Beat one, the fit.** `_print_tree` walks the tree with two queries per node.
The region is the whole walk; the states are the number of nodes in the subtree
being printed and the number of nodes in the whole document, and
`s2l/pick_nodes.py` tabulates real nodes spanning subtree sizes from 25 to
15,661 so a single index yields a whole sweep.

Declaring both states at once produced a formula drperf itself refused to stand
behind:

```
cost(n_nodes, n_total) = 10,634,764.1*n_nodes + 0*n_total + -1,972,730.6
    blocks: 8007 affine, 981 constant, 1267 irregular (0.3% of cost)
    negative constant: the counts curve over the observed values
                       (n log n, n^2, ...); the plane is a local approximation
```

The per-block test passes at 0.3%, and the tool still says the answer is wrong,
because the fitted constant is negative. Adding the product of the two states as
a third variable did not help either: within one document the product and the
node count are collinear. What does work is one fit per document, which turns
the curvature into a comparison of two slopes:

| document | instructions per heading printed | irregular |
|---|---|---|
| 10,684 nodes | 7,854,576.6 | 0.2% |
| 24,352 nodes | 17,930,326.6 | 0.0% |

**Beat two, the surprise: the slope is the document.** The two slopes stand in
the ratio 2.283; the two documents stand in the ratio 2.279. Printing one
heading costs a pass over the entire specification, so the walk is quadratic.
drperf attributes the slope to `sqlite3VdbeExec`, 4,695,606 instructions per
node inside the SQLite virtual machine, which points at the query rather than
at Python. The query plan is explicit about it:

```
sqlite> explain query plan
        SELECT node_id FROM nodes WHERE parent_id = ? ORDER BY ordinal;
  SCAN nodes USING INDEX nodes_parent_order
  USE TEMP B-TREE FOR ORDER BY
```

`SCAN`, not `SEARCH`. The one index that covers the column is
`nodes(document_id, parent_id, ordinal)`, and a query that constrains only
`parent_id` cannot seek into a composite index whose first column is missing.
So SQLite walks the whole index for every node and then sorts the survivors in
a temporary B-tree.

**Beat three, the fix.** The parent row already carries `document_id`, and no
child in any of the three shipped indexes has a different `document_id` from its
parent (checked: 0 of 35,540 parent/child pairs). Naming it in the query lets
the index seek and makes the ordering free. A second edit stops `SELECT *` from
loading `raw_text` and `normalized_text` in full for every node when `_summary`
reads 100 characters of one of them.

```
- "SELECT node_id FROM nodes WHERE parent_id = ? ORDER BY ordinal", (node_id,)
+ "SELECT node_id FROM nodes WHERE document_id = ? AND parent_id = ? ORDER BY ordinal",
+ (row["document_id"], node_id),

  SEARCH nodes USING INDEX nodes_parent_order (document_id=? AND parent_id=?)
```

**The same formula, re-derived after the fix:**

| document | before | after | factor |
|---|---|---|---|
| 10,684 nodes | 7,854,576.6 | 103,554.5 | 75.8x |
| 24,352 nodes | 17,930,326.6 | 109,027.6 | 164.5x |
| slope ratio between the two documents | 2.283 | 1.053 | |

The slope ratio falling to 1.053 is the statement that the quadratic is gone:
after the fix, printing a heading costs the same whatever the size of the
document it sits in.

**Instructions**, printing a 1,933-node subtree of the 24,352-node index:

| region | calls | before | after | change |
|---|---|---|---|---|
| `children_query` | 1,933 | 34,489,966,352 | 46,038,770 | -99.9% |
| `print_tree` | 1 | 34,671,724,854 | 224,310,841 | -99.4% |
| whole process | | 35,108,938,346 | 661,568,909 | -98.1% |
| per node visited | | 17,936,743 | 116,042 | 155x |

The formula predicted 17,930,327 instructions per node and the run measured
17,936,743, a difference of 0.04%.

**End to end**, the real CLI command, uninstrumented:

| command | stock | fixed | speedup |
|---|---|---|---|
| `index tree` on CXL 2.0 (10,684 nodes) | 10.75 s | 0.47 s | 22.9x |
| `index tree` on PTX 9.3 (24,352 nodes) | 70.00 s | 0.63 s | **111x** |
| `index subtree` on the largest PTX node | 44.94 s | 0.43 s | 104x |

The speedup grows with the document, which is what a removed quadratic looks
like. The index fix alone accounts for almost all of it: PTX `index tree` is
0.70 s with the query fix and 0.63 s with the narrowed `SELECT` as well.

**Equivalence.** `s2l/equiv.py` prints 60 trees, spanning every index, both the
headings-only and all-nodes modes and both depth limits, and digests the output:
identical across the stock tree, the query fix alone, and both fixes. The full
CLI output was then diffed directly on all three indexes, including
`--all-nodes` on CXL, 10,684 lines: identical.

**The same shape, four more times.** Grepping for the pattern the formula
exposed finds four further queries that filter `nodes` on `parent_id` without
`document_id`: `index children` in the CLI, one in the evidence query path and
two in the planner's scope resolution. They were not measured here, but they
cannot use the index either.

**The second quadratic, same loop applied again.** `index validate` was still
about 70 seconds, from a different cause: for every stored HTML anchor it
evaluates `//*[@id=$anchor or @name=$anchor]` against the parsed document, so
899 anchors each scan an 80,491-element DOM. Fitting it needed the product of
the two states before it fit at all, 100% irregular with the states alone and
7.5% with the product, and the formula then reads **5,617.5 instructions per
anchor-element pair**. The loop only asks whether a match exists, so one pass
collecting every `id` and `name` answers all of them. Three further child
queries with the same unusable-index shape as the tree walk were fixed the same
way, using a scalar subquery to supply `document_id`.

**Every affected command, end to end:**

| command | stock | fixed | speedup |
|---|---|---|---|
| `index tree` (PTX, 24,352 nodes) | 73.17 s | 0.69 s | **106x** |
| `index subtree` (largest PTX node) | 49.16 s | 0.48 s | 102x |
| `index tree` (CXL 2.0, 10,684 nodes) | 11.68 s | 0.40 s | 29x |
| `index validate` (PTX) | 72.14 s | 3.41 s | 21x |
| `index build` (PTX, from HTML source) | 69.10 s | 3.89 s | 18x |

`index build` is the tool's primary expensive operation, and a full rebuild from
the HTML source produces the same `semantic_digest` and the same validation
result; comparing the two databases table by table, every content table matches
exactly and only `created_at` timestamps differ. The findings are written up for
the project in `/home/ubuntu/spec2lean/bug_report.md`.

**Why this case is worth the two before it.** The cold-start case found real
work with a profiler and drperf only sized it. The per-step case needed a cost
function to see a coefficient. This one needed the cost function to see that a
*coefficient was not a constant*: the number of instructions per node was itself
proportional to a second state, which is what "quadratic" means and what no
single profile of a single input can show. The tool then refused the flat
formula by reporting a negative constant, which is the same guarantee working
from the other side.

