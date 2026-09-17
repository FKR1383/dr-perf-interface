"""Run spec2lean's anchor-resolution check over a chosen document and anchor count.

Usage: run_anchor.py [n_anchors=N] [n_elements=N]

The loop is the one in `validate_database`: for each stored HTML anchor, ask the
parsed document whether any element carries that id or name. The document is a
truncated copy of the real PTX HTML (see make_html.py) so DOM size is a state.
"""
import os, pathlib, sqlite3, sys

ROOT = pathlib.Path(__file__).resolve().parent
DB = "/home/ubuntu/spec2lean/indexes/ptx-9.3.sqlite"
DOC = "doc:9a971a2460dba1180a9a4721"
SIZES = [5001, 10001, 20001, 40001, 80001]

sys.path.insert(0, "/home/ubuntu/drperf/perfmark/python")
import perfmark
from lxml import html


def main():
    args = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k] = int(v)
    n_anchors = args.get("n_anchors", 8)
    want = args.get("n_elements", 20001)
    n_elements = min(SIZES, key=lambda s: abs(s - want))

    tree = html.parse(str(ROOT / "html" / f"ptx_{n_elements}.html"))

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    anchors = [
        r["html_anchor"]
        for r in con.execute(
            "SELECT html_anchor FROM nodes WHERE document_id = ? AND html_anchor IS NOT NULL "
            "ORDER BY node_id",
            (DOC,),
        )
    ][:n_anchors]

    # The scan visits every element for every anchor, so the cost is a product and
    # no plane in (n_anchors, n_elements) can express it. Declared exactly: the
    # product peaks near 1.3M here, small enough that no rescaling is needed, and
    # coarse units would blur the smallest cells past drperf's 5% tolerance.
    prod = len(anchors) * n_elements
    resolved = 0
    with perfmark.region(
        "anchor_check", n_anchors=len(anchors), n_elements=n_elements, an_prod=prod
    ):
        for anchor in anchors:
            matches = tree.xpath("//*[@id=$anchor or @name=$anchor]", anchor=anchor)
            if matches:
                resolved += 1
    print(f"n_anchors={len(anchors)} n_elements={n_elements} resolved={resolved}")


if __name__ == "__main__":
    main()
