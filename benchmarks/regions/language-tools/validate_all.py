#!/usr/bin/env python3
"""Validate every case in an isolated pinned worktree and write receipts."""
import argparse, hashlib, json, pathlib, subprocess, sys

HERE=pathlib.Path(__file__).resolve().parent
REGIONS=HERE.parent
PROJECT_REPOS={
 "sympy":"https://github.com/sympy/sympy.git", "sqlglot":"https://github.com/tobymao/sqlglot.git",
 "libcst":"https://github.com/Instagram/LibCST.git", "astroid":"https://github.com/pylint-dev/astroid.git",
 "jinja":"https://github.com/pallets/jinja.git", "pyparsing":"https://github.com/pyparsing/pyparsing.git",
 "lark":"https://github.com/lark-parser/lark.git", "cython":"https://github.com/cython/cython.git"}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser(); p.add_argument("--runtime-root",type=pathlib.Path,default=pathlib.Path("/tmp/ignored_runtime")); p.add_argument("--python",default=sys.executable); p.add_argument("--report",type=pathlib.Path,default=HERE/"validation-report.json"); a=p.parse_args()
 manifests=sorted((HERE/"cases").glob("*/case.json")); receipts=[]; prepared=set()
 for manifest in manifests:
  data=json.loads(manifest.read_text()); project=data["source"]["snapshot"].split("/")[3]; clone=a.runtime_root/project; work=a.runtime_root/f"lt-checkout-{project}"
  if not (clone/".git").exists(): subprocess.run(["git","clone",PROJECT_REPOS[project],str(clone)],check=True)
  if project not in prepared:
   subprocess.run(["git","-C",str(clone),"fetch","origin",data["source"]["revision"]],check=True,stdout=subprocess.DEVNULL)
   if not (work/".git").exists(): subprocess.run(["git","-C",str(clone),"worktree","add","--detach",str(work),data["source"]["revision"]],check=True,stdout=subprocess.DEVNULL)
   head=subprocess.check_output(["git","-C",str(work),"rev-parse","HEAD"],text=True).strip(); assert head==data["source"]["revision"],(project,head)
   prepared.add(project)
  patch=manifest.parent/"region.patch"; subprocess.run(["git","-C",str(work),"apply","--check",str(patch)],check=True); subprocess.run(["git","-C",str(work),"apply",str(patch)],check=True)
  try:
   proc=subprocess.run([a.python,str(REGIONS/"collect.py"),"test",data["id"],"--python",a.python,"--source-root",str(work)],cwd=REGIONS.parents[1],text=True,capture_output=True)
  finally: subprocess.run(["git","-C",str(work),"apply","-R",str(patch)],check=True)
  marker=None
  for line in proc.stdout.splitlines():
   if line.startswith('{"marker_hits"'): marker=json.loads(line)
  resources={r["destination"]:r["sha256"] for r in data["tests"].get("resources",[])}
  receipts.append({"id":data["id"],"revision":data["source"]["revision"],"path":data["source"]["path"],"region":data["region"],"source_sha256":data["source"]["sha256"],"patch_sha256":sha(patch),"test_sha256":sha(manifest.parent/"tests"/"test_case.py"),"resource_sha256":resources,"returncode":proc.returncode,"marker_hits":None if marker is None else marker["marker_hits"].get(data["id"],0)})
  print(data["id"],"PASS" if proc.returncode==0 else "FAIL",file=sys.stderr)
 freeze=subprocess.check_output([a.python,"-m","pip","freeze","--all"],text=True).splitlines()
 report={"schema_version":1,"runner":"validate_all.py","environment":{"python":sys.version,"executable":a.python,"pip_freeze":freeze,"pip_freeze_sha256":hashlib.sha256(("\n".join(freeze)+"\n").encode()).hexdigest()},"case_count":len(receipts),"passed":sum(bool(r["returncode"]==0 and r["marker_hits"]) for r in receipts),"receipts":receipts}
 a.report.write_text(json.dumps(report,indent=2)+"\n")
 if report["passed"] != report["case_count"]: raise SystemExit(1)

if __name__=="__main__": main()
