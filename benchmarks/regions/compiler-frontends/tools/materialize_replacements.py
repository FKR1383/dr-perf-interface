#!/usr/bin/env python3
"""Assign reviewed coverage proposals to failed case IDs and record evidence."""
import argparse, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument("--proposals",type=Path,required=True);p.add_argument("--failed-summary",type=Path,required=True);a=p.parse_args()
    proposed=json.loads(a.proposals.read_text());summary=json.loads(a.failed_summary.read_text())
    failed=[x["id"] for x in summary["results"] if x["status"]!="region-verified"]
    options=proposed["proposals"]
    if len(options)!=len(failed):raise SystemExit(f"need {len(failed)} proposals, got {len(options)}")
    manifests={json.loads(p.read_text())["id"]:json.loads(p.read_text()) for p in (ROOT/"cases").glob("*/case.json")}
    remaining=options[:];assign={}
    # Retain phase identity where possible, then fill with the reviewed diverse pool.
    for cid in failed:
        phase=manifests[cid]["phase"]
        index=next((i for i,x in enumerate(remaining) if x["phase"]==phase),0)
        assign[cid]=remaining.pop(index)
        witness=assign[cid]["witness"]
        assign[cid]["witness_spec"]=json.loads((ROOT/"cases"/witness/"tests/spec.json").read_text())
    evidence={"schema_version":1,"kind":"coverage-guided compiler region replacements",
      "revision":summary["revision"],"runner_sha256":summary["runner_sha256"],
      "failed_summary_sha256":hashlib.sha256(a.failed_summary.read_bytes()).hexdigest(),
      "proposal_sha256":hashlib.sha256(a.proposals.read_bytes()).hexdigest(),"replacements":assign}
    (ROOT/"tools/replacements.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(f"materialized {len(assign)} reviewed replacement mappings")

if __name__=="__main__":main()
