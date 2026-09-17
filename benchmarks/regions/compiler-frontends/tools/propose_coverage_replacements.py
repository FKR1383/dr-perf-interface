#!/usr/bin/env python3
"""Propose reachable replacement functions from pinned Clang source coverage.

This is read-only. It never rewrites cases; its output records the witness,
phase, symbol, and region consumed by the reviewed generator workflow.
"""
import argparse
import difflib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("generate_cases", HERE / "generate_cases.py")
gen = importlib.util.module_from_spec(spec); sys.modules[spec.name]=gen; spec.loader.exec_module(gen)

def line_map(pristine: list[str], marked: list[str]):
    result = {}
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(a=pristine, b=marked, autojunk=False).get_opcodes():
        if tag == "equal":
            for offset in range(b1 - b0): result[b0 + offset + 1] = a0 + offset + 1
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--coverage",type=Path,required=True,action="append");p.add_argument("--failed-summary",type=Path,required=True)
    p.add_argument("--marked-source",type=Path,required=True);p.add_argument("--pristine",type=Path,default=gen.CHECKOUT);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    failed={x["id"] for x in json.loads(a.failed_summary.read_text())["results"] if x["status"]!="region-verified"}
    current={}
    for manifest in (gen.ROOT/"cases").glob("*/case.json"):
        d=json.loads(manifest.read_text());current[(d["source"]["path"],d["region"]["start_line"],d["region"]["end_line"])]=d["id"]
    cache={};demangled={};options=[]
    results=[]
    for directory in a.coverage:results.extend(directory.glob("cf-*.json"))
    for result in sorted(results):
        row=json.loads(result.read_text()); witness=row["id"]
        if row["returncode"]:continue
        for f in row["functions"]:
            rel=f["source"]
            if not rel.startswith(("clang/lib/", "llvm/lib/AsmParser/", "llvm/lib/IR/")):continue
            pristine=a.pristine/rel;marked=a.marked_source/rel
            if not pristine.is_file() or not marked.is_file():continue
            if rel not in cache:
                cs=gen.candidates(pristine); lm=line_map(pristine.read_text(errors="replace").splitlines(),marked.read_text(errors="replace").splitlines())
                cache[rel]=(cs,lm)
            cs,lm=cache[rel]; original_line=f.get("original_line") or lm.get(f["marked_line"])
            if original_line is None:continue
            matches=[c for c in cs if c.start<=original_line<=c.opening+1]
            if not matches:continue
            name=f["name"]
            mangled=name.split(":",1)[1] if ":_Z" in name else name
            if name not in demangled:demangled[name]=subprocess.check_output(["c++filt",mangled],text=True).strip()
            def symbol_matches(c):
                qualified=c.symbol.lstrip("~")
                if "::" in qualified:return qualified in demangled[name]
                return qualified.split("::")[-1] in demangled[name].split("(",1)[0]
            matches=[c for c in matches if symbol_matches(c)]
            if not matches:continue
            c=min(matches,key=lambda x:abs(x.opening-original_line));key=(rel,c.start,c.end)
            if key in current:continue
            body="".join(pristine.read_text(errors="replace").splitlines(True)[c.opening-1:c.end])
            traits=[label for needle,label in (("for (","loop"),("while (","loop"),("Parse","parse"),("Lookup","lookup"),("copy","copy"),("Visit","traversal"),("Diagn","diagnostic"),("SmallVector","growing-container")) if needle in body]
            options.append({"witness":witness,"source":rel,"symbol":c.symbol,"start_line":c.start,"end_line":c.end,"phase":gen.phase_for(rel),"count":f["count"],"candidate_score":c.score,"traits":sorted(set(traits)),"coverage_name":f["name"],"demangled_name":demangled[name]})
    # Structural score and reviewed cost signals lead; raw call count is only a
    # tie-breaker so tiny ubiquitous helpers do not dominate the proposals.
    options.sort(key=lambda x:(not bool(x["traits"]),-x["candidate_score"],-x["count"],x["source"],x["start_line"]))
    chosen=[];used=set();phase_counts={}
    for item in options:
        key=(item["source"],item["start_line"],item["end_line"])
        if key in used or phase_counts.get(item["phase"],0)>=35:continue
        used.add(key);chosen.append(item);phase_counts[item["phase"]]=phase_counts.get(item["phase"],0)+1
        if len(chosen)>=len(failed):break
    out={"kind":"coverage-guided replacement proposals","failed_case_count":len(failed),"proposal_count":len(chosen),"proposals":chosen}
    a.out.write_text(json.dumps(out,indent=2)+"\n");print(f"proposed {len(chosen)} reachable distinct functions for {len(failed)} failed cases")

if __name__=="__main__":main()
