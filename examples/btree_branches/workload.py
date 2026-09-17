"""Semantic path summaries of real BTrees 6.1 integer-key lookup.

The replay follows BTREE_SEARCH and BUCKET_SEARCH in upstream 6.1. It reads
the actual tree's serialization state before measurement, not a guessed shape.
It returns event counts, never instruction counts or fitted coefficients.
"""
import json
from pathlib import Path
import random
import sys

from BTrees.IIBTree import IIBTree

sys.path.insert(0, str(Path(__file__).resolve().parent / "bin"))
from _btree_measure import measure


class SmallNodes(IIBTree):
    # Documented tuning knobs; small fanout exercises several levels cheaply.
    max_leaf_size = 8
    max_internal_size = 8


def path_summary(tree, key):
    counts = dict(depth=0, internal_lt=0, internal_gt=0, internal_eq=0,
                  leaf_lt=0, leaf_gt=0, leaf_eq=0)
    path = []
    node = tree
    while isinstance(node, IIBTree):
        counts["depth"] += 1
        state = node.__getstate__()
        assert len(state) == 2, "workload excludes single-bucket serialization shortcut"
        entries = state[0]
        children = entries[::2]
        separators = entries[1::2]
        lo, hi = 0, len(children)
        i = hi >> 1
        outcomes = []
        while i > lo:
            pivot = separators[i - 1]
            if pivot < key:
                counts["internal_lt"] += 1
                outcomes.append("lt")
                lo = i
            elif pivot > key:
                counts["internal_gt"] += 1
                outcomes.append("gt")
                hi = i
            else:
                counts["internal_eq"] += 1
                outcomes.append("eq")
                break
            i = (lo + hi) >> 1
        path.append(dict(children=len(children), child=i, outcomes=outcomes))
        node = children[i]
    entries = node.__getstate__()[0]
    keys = entries[::2]
    lo, hi = 0, len(keys)
    i = hi >> 1
    leaf_outcomes = []
    while lo < hi:
        if keys[i] < key:
            counts["leaf_lt"] += 1
            leaf_outcomes.append("lt")
            lo = i + 1
        elif keys[i] == key:
            counts["leaf_eq"] += 1
            leaf_outcomes.append("eq")
            break
        else:
            counts["leaf_gt"] += 1
            leaf_outcomes.append("gt")
            hi = i
        i = (lo + hi) >> 1
    assert counts["leaf_eq"] == 1 and entries[2*i+1] == tree[key] == 7
    counts["internal_comparisons"] = sum(counts["internal_" + s] for s in ("lt", "gt", "eq"))
    counts["leaf_comparisons"] = sum(counts["leaf_" + s] for s in ("lt", "gt", "eq"))
    counts["comparisons"] = counts["internal_comparisons"] + counts["leaf_comparisons"]
    counts["lt"] = counts["internal_lt"] + counts["leaf_lt"]
    counts["gt"] = counts["internal_gt"] + counts["leaf_gt"]
    counts["eq"] = counts["internal_eq"] + counts["leaf_eq"]
    counts["descents"] = counts["depth"] - 1
    return counts, path, dict(size=len(keys), outcomes=leaf_outcomes)


ANNOTATIONS = {
    "size_depth_rank": ("n", "depth", "rank"),
    "depth_comparisons": ("depth", "comparisons"),
    "comparison_kinds": ("depth", "internal_comparisons", "leaf_comparisons"),
    "semantic4": ("depth", "internal_comparisons", "leaf_comparisons", "lt"),
    "audit": ("case_id",),
}


def main():
    rows = []
    repeats = 256
    for n in (128, 512, 2048):
        for order in ("ascending", "descending", "shuffled"):
            tree = SmallNodes()
            indices = list(range(n))
            if order == "descending": indices.reverse()
            if order == "shuffled": random.Random(1729).shuffle(indices)
            for i in indices: tree[1000 + 2*i] = 7
            tree._check()
            ranks = sorted({0, 1, n//8, n//4, n//2, 3*n//4, n-2, n-1})
            for rank in ranks:
                key = 1000 + 2*rank
                counts, path, leaf = path_summary(tree, key)
                row = dict(case_id=len(rows), n=n, rank=rank, key=key, order=order,
                           **counts, path=path, leaf=leaf)
                # Warm up lookup before measuring a resident, read-only tree.
                assert tree[key] == 7
                for region, names in ANNOTATIONS.items():
                    features = tuple(row[name] for name in names)
                    for _ in range(2):
                        assert measure(region, tree, key, names, features, repeats) == 7*repeats
                rows.append(row)
    Path(sys.argv[1]).write_text(json.dumps(dict(repeats=repeats, cases=rows), indent=2) + "\n")
    print(f"PASS: {len(rows)} tree/query cases; {len(rows)*len(ANNOTATIONS)*2*repeats} checked lookups")


if __name__ == "__main__":
    main()
