"""Insert perfmark regions into a copy of the spec2lean package."""
import pathlib, sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "s2l/mark_pkg")


def edit(rel, subs, add_import=True):
    p = ROOT / rel
    s = p.read_text()
    for old, new in subs:
        if new in s:
            continue
        if s.count(old) != 1:
            continue
        s = s.replace(old, new)
    if add_import and "import perfmark" not in s:
        lines = s.split("\n")
        i = 1 if lines and lines[0].startswith("from __future__") else 0
        lines.insert(i, "import perfmark")
        s = "\n".join(lines)
    p.write_text(s)
    print("marked", rel)


edit("cli.py", [
    # the whole walk, with the size of the subtree it is asked to print
    ("""    def visit(node_id: str, shown_depth: int, structural_depth: int) -> None:
        row = connection.execute(
            "SELECT node_id, document_id, node_type, section_number, title, "
            "page_start, html_anchor, substr(normalized_text, 1, 100) AS normalized_text "
            "FROM nodes WHERE node_id = ?",
            (node_id,),
        ).fetchone()
        if row is None:
            return""",
     """    _n_nodes = int(__import__("os").environ.get("S2L_PM_NODES", "0"))
    _n_total = int(__import__("os").environ.get("S2L_PM_TOTAL", "0"))
    _n_prod = int(__import__("os").environ.get("S2L_PM_PROD", "0"))

    def visit(node_id: str, shown_depth: int, structural_depth: int) -> None:
        with perfmark.region("visit_node", tag=1):
            row = connection.execute(
                "SELECT * FROM nodes WHERE node_id = ?", (node_id,)
            ).fetchone()
        if row is None:
            return"""),
    ("""        for child in connection.execute(
            "SELECT node_id FROM nodes WHERE parent_id = ? ORDER BY ordinal", (node_id,)
        ):
            visit(child["node_id"], next_shown, structural_depth + 1)""",
     """        with perfmark.region("children_query", tag=2):
            _kids = connection.execute(
                "SELECT node_id FROM nodes WHERE parent_id = ? ORDER BY ordinal", (node_id,)
            ).fetchall()
        for child in _kids:
            visit(child["node_id"], next_shown, structural_depth + 1)"""),
    ("""        for child in connection.execute(
            "SELECT node_id FROM nodes WHERE document_id = ? AND parent_id = ? "
            "ORDER BY ordinal",
            (row["document_id"], node_id),
        ):
            visit(child["node_id"], next_shown, structural_depth + 1)""",
     """        with perfmark.region("children_query", tag=2):
            _kids = connection.execute(
                "SELECT node_id FROM nodes WHERE document_id = ? AND parent_id = ? "
                "ORDER BY ordinal",
                (row["document_id"], node_id),
            ).fetchall()
        for child in _kids:
            visit(child["node_id"], next_shown, structural_depth + 1)"""),
    ("""    for root in roots:
        visit(root, 0, 0)""",
     """    with perfmark.region(
            "print_tree", n_nodes=_n_nodes, n_total=_n_total, nn_prod=_n_prod
        ):
        for root in roots:
            visit(root, 0, 0)"""),
])
print("done")
