"""Print one subtree of a spec2lean index, for drperf.

Usage: run_tree.py [n_nodes=N] [total=N]

`n_nodes` selects a node whose subtree has (approximately) that many nodes, from a
table computed once by pick_nodes.py. `total` selects which index to open, so the
per-node cost can be measured against the size of the whole document as well as the
size of the subtree being printed.
"""
import json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
TREE = os.environ.get("S2L_TREE", "mark_pkg")


def main():
    args = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k] = int(v)

    table = json.loads((ROOT / "nodes.json").read_text())
    total = args.get("total", 24352)
    want = args.get("n_nodes", 400)

    entry = min(table, key=lambda e: (abs(e["total"] - total), abs(e["subtree"] - want)))
    for e in table:
        if e["total"] == total:
            break
    else:
        entry = min(table, key=lambda e: abs(e["subtree"] - want))
    cands = [e for e in table if e["total"] == total] or table
    entry = min(cands, key=lambda e: abs(e["subtree"] - want))

    os.environ["S2L_PM_NODES"] = str(entry["subtree"])
    os.environ["S2L_PM_TOTAL"] = str(entry["total"])
    # The product, in coarse units: a plane in (n_nodes, n_total) cannot express
    # a cost that is proportional to both, and drperf reports the miss as a
    # negative constant. Coarse units keep this column comparable in magnitude to
    # the others when the least-squares system is solved.
    os.environ["S2L_PM_PROD"] = str(entry["subtree"] * entry["total"] // 1024)

    # import the package under test as `spec2lean`
    import importlib.util
    pkg_dir = ROOT / TREE
    spec = importlib.util.spec_from_file_location(
        "spec2lean", pkg_dir / "__init__.py", submodule_search_locations=[str(pkg_dir)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["spec2lean"] = module
    spec.loader.exec_module(module)

    from spec2lean.database import connect
    from spec2lean.cli import _print_tree

    devnull = open(os.devnull, "w")
    real_stdout = sys.stdout
    sys.stdout = devnull
    try:
        with connect(pathlib.Path(entry["database"]), read_only=True) as connection:
            _print_tree(connection, [entry["node_id"]], headings_only=True, max_depth=None)
    finally:
        sys.stdout = real_stdout
        devnull.close()
    print(f"subtree={entry['subtree']} total={entry['total']} db={pathlib.Path(entry['database']).name}")


if __name__ == "__main__":
    main()
