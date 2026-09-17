#!/usr/bin/env python3
"""Promote compiler cases only from hash-bound native entry receipts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_results(paths):
    results = {}
    evidence = {}
    for path in paths:
        payload = json.loads(path.read_text())
        rows = payload.get("results", [payload])
        for row in rows:
            results[row["id"]] = row
            evidence[row["id"]] = str(path)
    return results, evidence


def verify(case_dir, manifest, receipt):
    cid = manifest["id"]
    assert receipt["status"] == "region-verified", f"{cid}: receipt did not verify region"
    assert receipt["source"] == manifest["source"], f"{cid}: source identity changed"
    assert receipt["region"] == manifest["region"], f"{cid}: region identity changed"
    assert receipt["patch_sha256"] == digest(case_dir / "region.patch"), f"{cid}: patch changed"
    assert receipt["spec_sha256"] == digest(case_dir / "tests/spec.json"), f"{cid}: spec changed"
    assert receipt.get("binary_sha256"), f"{cid}: binary hash missing"
    for name, expected in receipt["test_assets_sha256"].items():
        asset = case_dir / name
        if not asset.exists():
            resource = next(r for r in manifest["tests"].get("resources", []) if r["destination"] == name)
            asset = case_dir / resource["source"]
        assert digest(asset) == expected, f"{cid}: test asset changed: {name}"
    sizes = [row["size"] for row in receipt["rows"]]
    assert sizes == [4, 16, 64], f"{cid}: expected exact sizes 4, 16, 64; got {sizes}"
    assert all(row["returncode"] == 0 and row["target_entries"] > 0 for row in receipt["rows"]), \
        f"{cid}: assertions or native entry failed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("summaries", nargs="+", type=Path,
                        help="Summary or individual receipt files; later files override earlier ones")
    parser.add_argument("--write", action="store_true", help="Update manifests after all receipts pass")
    args = parser.parse_args()
    receipts, evidence = load_results(args.summaries)
    manifests = sorted((ROOT / "cases").glob("cf-*/case.json"))
    assert len(manifests) == 250, f"expected 250 cases, found {len(manifests)}"
    pending = []
    for path in manifests:
        manifest = json.loads(path.read_text())
        cid = manifest["id"]
        assert cid in receipts, f"{cid}: no receipt"
        receipt = receipts[cid]
        verify(path.parent, manifest, receipt)
        pending.append((path, manifest, receipt, evidence[cid]))
    if args.write:
        for path, manifest, receipt, proof in pending:
            manifest["status"] = "region-verified"
            manifest["build_status"] = "built-and-region-verified"
            manifest["tests"]["validation"] = {
                "status": "region-verified",
                "details": "Assertions passed and the exact marked native region was entered at structural sizes 4, 16, and 64 on the pinned instrumented LLVM build.",
                "evidence": proof,
                "binary_sha256": receipt["binary_sha256"],
                "spec_sha256": receipt["spec_sha256"],
                "patch_sha256": receipt["patch_sha256"],
            }
            manifest["tests"]["coverage_note"] = "Hash-bound native entry evidence is recorded in the validation receipt. It establishes reachability, not cost or speedup."
            path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"verified": len(pending), "updated": bool(args.write)}))


if __name__ == "__main__":
    main()
