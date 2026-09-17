#!/usr/bin/env python3
"""Reject compiler cases whose test command cannot enter the selected subsystem."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    failures = []
    replacement_path=ROOT/"tools/replacements.json"
    replacements=json.loads(replacement_path.read_text()).get("replacements",{}) if replacement_path.exists() else {}
    for manifest_path in sorted((ROOT / "cases").glob("*/case.json")):
        case = json.loads(manifest_path.read_text())
        spec = json.loads((manifest_path.parent / "tests/spec.json").read_text())
        rel = case["source"]["path"]
        phase = case["phase"]
        scenario = spec["scenario"]
        tool = spec["compiler"]
        required = None
        if case["id"] in replacements:
            replacement=replacements[case["id"]]
            required=(replacement["source"]==rel and replacement["symbol"]==case["region"]["symbol"] and spec.get("workload_phase") is not None)
        elif "SemaCodeComplete" in rel: required = (scenario.endswith("completion"))
        elif phase == "formatting": required = (tool == "clang-format")
        elif "DependencyScanning" in rel: required = (tool == "clang-scan-deps")
        elif "Tooling/Syntax" in rel: required = (spec.get("harness_status") == "missing-custom-syntax-tree-harness")
        elif "ASTImporter" in rel or scenario in {"ast-structural-equivalence", "ast-import-shape"}: required = (tool == "clang-import-test")
        elif phase == "source-tooling": required = (tool == "clang-check")
        elif phase == "serialization": required = (tool == "clang")  # runner performs both PCH write and read
        elif phase == "ir-parsing": required = (spec["fixtures"][0]["source"].lstrip().startswith(("define", "@")))
        elif phase == "static-analysis": required = ("--analyze" in spec["flags"])
        else: required = (tool == "clang")
        sizes = [x["size"] for x in spec.get("fixtures", [])]
        sources = [x["source"] for x in spec.get("fixtures", [])]
        if required is not True: failures.append(f"{case['id']}: subsystem command mismatch")
        if sizes != [4, 16, 64] or len(set(sources)) != 3:
            failures.append(f"{case['id']}: missing distinct 4/16/64 structural inputs")
        if spec.get("target_symbol") != case["region"]["symbol"] or spec.get("target_source") != rel:
            failures.append(f"{case['id']}: spec target mismatch")
    if failures: raise SystemExit("\n".join(failures))
    print("Audited 250 mappings: subsystem tools, exact targets, and distinct 4/16/64 inputs.")

if __name__ == "__main__": main()
