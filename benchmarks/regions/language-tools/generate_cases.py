#!/usr/bin/env python3
"""Generate the pinned language-tools region collection from local upstream clones."""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = Path("/tmp/ignored_runtime")
PROJECTS = {
    "sympy": ("https://github.com/sympy/sympy", "sympy", 44),
    "sqlglot": ("https://github.com/tobymao/sqlglot", "sqlglot", 38),
    "libcst": ("https://github.com/Instagram/LibCST", "libcst", 30),
    "astroid": ("https://github.com/pylint-dev/astroid", "astroid", 32),
    "jinja": ("https://github.com/pallets/jinja", "src/jinja2", 28),
    "pyparsing": ("https://github.com/pyparsing/pyparsing", "pyparsing", 25),
    "lark": ("https://github.com/lark-parser/lark", "lark", 28),
    "cython": ("https://github.com/cython/cython", "Cython", 25),
}
VERIFIED = {f"lt-{i:03d}" for i in range(1, 251)}

def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def qname(node, parents):
    names = [p.name for p in parents if isinstance(p, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
    return ".".join(names + [node.name])

def score(node):
    counts = {t: 0 for t in (ast.For, ast.While, ast.comprehension, ast.Call, ast.If, ast.Dict, ast.Set)}
    for n in ast.walk(node):
        for t in counts:
            if isinstance(n, t): counts[t] += 1
    lines = node.end_lineno - node.lineno + 1
    nested = counts[ast.For] + counts[ast.While] + counts[ast.comprehension]
    return nested * 12 + counts[ast.Call] * 2 + counts[ast.If] * 3 + min(lines, 80)

def statement_start(node):
    return min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])

def candidates(root: Path, subdir: str):
    found=[]
    for p in (root/subdir).rglob("*.py"):
        rel=p.relative_to(root)
        if any(x in rel.parts for x in ("tests", "test", "benchmarks", "vendor", "vendored", "_vendor")) or "generated" in p.name: continue
        try: tree=ast.parse(p.read_bytes())
        except (SyntaxError, UnicodeDecodeError): continue
        stack=[]
        def walk(body, parents):
            for n in body:
                if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    lines=n.end_lineno-n.lineno+1
                    s=score(n)
                    if 10 <= lines <= 180 and s >= 35 and not n.name.startswith("test"):
                        body0=n.body[1:] if n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str) else n.body
                        # Indenting a nested multiline string changes its value even
                        # though the wrapper looks textual. Exclude those so removing
                        # the marker recovers an exactly identical AST.
                        multiline = any(isinstance(x, ast.Constant) and isinstance(x.value, str) and "\n" in x.value and x is not (n.body[0].value if n.body and isinstance(n.body[0], ast.Expr) else None) for x in ast.walk(n))
                        if body0 and not multiline: found.append((s,p,rel,n,qname(n,parents),statement_start(body0[0]),n.end_lineno))
                    walk(n.body,parents+[n])
                elif isinstance(n,ast.ClassDef): walk(n.body,parents+[n])
        walk(tree.body,[])
    # Diversify by file before taking second functions from the same file.
    found.sort(key=lambda x:(-x[0],str(x[2]),x[3].lineno))
    chosen=[]; rounds={}
    while found:
        best=min(found,key=lambda x:(rounds.get(str(x[2]),0),-x[0]))
        found.remove(best); chosen.append(best); rounds[str(best[2])]=rounds.get(str(best[2]),0)+1
    return chosen

def marked_text(raw: str, node, marker: str):
    lines=raw.splitlines(keepends=True)
    newline="\r\n" if "\r\n" in raw else "\n"
    # Import after shebang/encoding and module docstring via AST-safe insertion.
    tree=ast.parse(raw); insert=0
    if tree.body and isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Constant) and isinstance(tree.body[0].value.value,str):
        insert=tree.body[0].end_lineno
    futures=[n.end_lineno for n in tree.body if isinstance(n,ast.ImportFrom) and n.module=="__future__"]
    if futures: insert=max(futures)
    lines.insert(insert,"import perfmark"+newline)
    shift=1 if insert < node.lineno else 0
    first=node.body[1] if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str) and len(node.body)>1 else node.body[0]
    start=statement_start(first)-1+shift; end=node.end_lineno+shift
    indent=lines[start][:len(lines[start])-len(lines[start].lstrip())]
    lines.insert(start,indent+f'with perfmark.region("{marker}"):'+newline)
    for i in range(start+1,end+1):
        if lines[i].strip(): lines[i]="    "+lines[i]
    return "".join(lines)

def main():
    if (HERE/"cases").exists(): shutil.rmtree(HERE/"cases")
    if (HERE/"upstream").exists(): shutil.rmtree(HERE/"upstream")
    (HERE/"cases").mkdir(parents=True); (HERE/"upstream").mkdir()
    marker_probe=HERE.parent/"support"/"marker_probe.py"
    probe_hash=digest(marker_probe)
    workloads=HERE/"test-support"/"workloads.py"
    workloads_hash=digest(workloads)
    idx=1
    for project,(repo,subdir,want) in PROJECTS.items():
        root=RUNTIME/project
        revision=__import__("subprocess").check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        license_file=next((p for p in root.iterdir() if p.is_file() and p.name.upper().startswith(("LICENSE","COPYING"))),None)
        if license_file:
            dst=HERE/"upstream"/project/license_file.name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(license_file,dst)
        coverage_path=RUNTIME/f"{project}-workload-cov.json"
        coverage=json.loads(coverage_path.read_text())["files"]
        selected=[]
        for candidate in candidates(root,subdir):
            _,source,relative,_,_,start,end=candidate
            entry=coverage.get(relative.as_posix()) or coverage.get(str(source))
            if entry and any(start <= line <= end for line in entry["executed_lines"]): selected.append(candidate)
        selected=selected[:want]
        if len(selected)<want: raise RuntimeError(f"{project}: only {len(selected)} candidates")
        for rank,(hot,p,rel,node,symbol,start,end) in enumerate(selected,1):
            cid=f"lt-{idx:03d}"; idx+=1
            snap=HERE/"upstream"/project/rel; snap.parent.mkdir(parents=True,exist_ok=True)
            raw=p.read_bytes().decode("utf-8"); marked=marked_text(raw,node,cid)
            snap.write_bytes(raw.encode("utf-8"))
            case=HERE/"cases"/cid; (case/"tests").mkdir(parents=True)
            diff="".join(difflib.unified_diff(raw.splitlines(True),marked.splitlines(True),fromfile=f"a/{rel.as_posix()}",tofile=f"b/{rel.as_posix()}"))
            (case/"region.patch").write_text(diff)
            title=f"{project} {symbol} body"
            data={"schema_version":1,"id":cid,"title":title,"language":"python",
              "source":{"repository":repo,"revision":revision,"path":rel.as_posix(),"snapshot":f"../../upstream/{project}/{rel.as_posix()}","sha256":digest(snap)},
              "region":{"symbol":symbol,"start_line":start,"end_line":end,"kind":"function"},
              "marker":{"kind":"python-context","name":cid,"pcvs":[]},"status":"collected","build_status":"not-built","phase":"language-tooling",
              "workload":{"description":f"Exercise {symbol} with bounded, varied {project} inputs and assert stable output or round-trip behavior.","command":["{python}","tests/test_case.py","--source-root","{source_root}"]},
              "source_family":f"{project}:{rel.as_posix()}:{symbol}","citations":[f"{repo}/blob/{revision}/{rel.as_posix()}"],
              "tests":{"files":["tests/test_case.py"],"resources":[{"source":"../../../support/marker_probe.py","destination":"tests/marker_probe.py","sha256":probe_hash},{"source":"../../test-support/workloads.py","destination":"tests/workloads.py","sha256":workloads_hash}],"command":["{python}","tests/test_case.py","--source-root","{source_root}"],
                "validation":{"status":"region-verified" if cid in VERIFIED else "not-run","details":("Passed in the pinned editable project checkout under Python 3.12. Varied valid inputs passed concrete value or round-trip assertions and marker_probe observed the named region." if cid in VERIFIED else "A dependency-matched pinned checkout is required. The workload uses varied valid project inputs, concrete output or round-trip assertions, and fails unless the named marker is entered.")},
                "coverage_note":"Runs pinned parser/compiler/rewriter APIs, checks concrete results, and requires named marker entry."}}
            (case/"case.json").write_text(json.dumps(data,indent=2)+"\n")
            (case/"task.md").write_text(f"# {title}\n\nInvestigate the cost of the marked `{symbol}` body under small, medium, and structurally nested inputs. Preserve observable behavior and report any performance-critical variables supported by measurements.\n")
            (case/"reference.md").write_text(f"# Selection evidence\n\nPinned upstream: [{rel.as_posix()}]({repo}/blob/{revision}/{rel.as_posix()}) at `{revision}`. The function scored {hot} in a structural scan for loops, comprehensions, calls, branches, and collection construction. This is provenance and an optimization lead, not ground truth. Nested scans, repeated tree conversion, cache misses, and intermediate allocation are plausible sources of several-fold improvement and must be measured.\n")
            test=f'''import argparse, pathlib, sys\nfrom marker_probe import Probe\nfrom workloads import run\np=argparse.ArgumentParser(); p.add_argument("--source-root",required=True); a=p.parse_args()\nroot=pathlib.Path(a.source_root); target=(root/{rel.as_posix()!r}).resolve(); assert target.is_file(), target\nsys.path.insert(0,str(root/"src")); sys.path.insert(0,str(root)); probe=Probe(); run({project!r})\nloaded={{pathlib.Path(m.__file__).resolve() for m in sys.modules.values() if getattr(m,"__file__",None)}}\nassert target in loaded, f"marked source was not loaded from supplied checkout: {{target}}"\nprobe.finish({cid!r})\n'''
            (case/"tests"/"test_case.py").write_text(test)
    assert idx == 251, idx

if __name__ == "__main__": main()
