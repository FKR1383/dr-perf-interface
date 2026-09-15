#!/usr/bin/env python3
"""Reproduce the general-libraries region collection from pinned checkouts."""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPOS = [
    ("networkx", "https://github.com/networkx/networkx", "4e74880b0da01977da79915167c64e5c2af38b47", 97),
    ("numpy", "https://github.com/numpy/numpy", "d8c7dad6638b623b79da658cafd9a86c8717630e", 35),
    ("pandas", "https://github.com/pandas-dev/pandas", "a290443f9e0f1dee4ea6aa9d9a5effb8ba5dbaee", 35),
    ("urllib3", "https://github.com/urllib3/urllib3", "43c68c8b43a9dcb44ed2cf4ec91384ca0d46b37d", 14),
    ("requests", "https://github.com/psf/requests", "dae7ef63b4df6eded86637f251fc4e3a06c3b479", 15),
    ("packaging", "https://github.com/pypa/packaging", "10590c194edb33c82f84a127883d6097c56b7840", 20),
    ("jsonschema", "https://github.com/python-jsonschema/jsonschema", "865c27fc3df08a082740d7743583795235fdfe81", 15),
    ("attrs", "https://github.com/python-attrs/attrs", "8f767776326faaed11e6c2974798787f6e19b343", 10),
    ("pathspec", "https://github.com/cpburnz/python-pathspec", "f0fb3f4aaaca490d7667e4dc1d565d52a25158b0", 9),
]
REGION_VERIFIED={
    "gl-001","gl-003","gl-004","gl-006","gl-007","gl-008","gl-009","gl-010",
    "gl-011","gl-012","gl-013","gl-014","gl-015","gl-016","gl-018","gl-020",
    "gl-021","gl-022","gl-023","gl-026","gl-030","gl-031","gl-034",
    "gl-035","gl-036","gl-037","gl-039","gl-041","gl-042","gl-043","gl-044","gl-045",
    "gl-046","gl-047","gl-048","gl-049","gl-050","gl-053","gl-055","gl-057",
    "gl-058","gl-059","gl-062","gl-063","gl-064","gl-065","gl-066","gl-067",
    "gl-068","gl-070","gl-072","gl-073","gl-074","gl-076","gl-077","gl-079","gl-080","gl-081",
    "gl-085","gl-086","gl-089","gl-090","gl-091","gl-092","gl-094","gl-095",
    "gl-096",
    "gl-002","gl-005","gl-017","gl-024","gl-029","gl-054","gl-069","gl-071",
    "gl-052","gl-056","gl-075","gl-078","gl-083","gl-084","gl-087","gl-088","gl-093",
    "gl-182",
    "gl-177","gl-178","gl-183","gl-188","gl-190","gl-192","gl-197","gl-206",
    "gl-208","gl-212","gl-216","gl-232","gl-234","gl-235","gl-236","gl-237",
    "gl-240","gl-241","gl-242","gl-243","gl-245","gl-246","gl-247","gl-250",
    "gl-169","gl-171","gl-173","gl-175","gl-176","gl-180","gl-181","gl-184","gl-185","gl-189","gl-191",
    "gl-193","gl-194","gl-195","gl-196","gl-198","gl-200","gl-202","gl-203",
    "gl-204","gl-207","gl-211","gl-233","gl-239","gl-248","gl-249",
    "gl-172","gl-209","gl-213","gl-215","gl-238","gl-244","gl-144","gl-153",
    "gl-098","gl-099","gl-100","gl-101","gl-105","gl-106","gl-110","gl-111",
    "gl-113","gl-114","gl-116","gl-117","gl-120","gl-121",
    "gl-122","gl-123","gl-124","gl-125","gl-128","gl-129","gl-130","gl-131","gl-132",
    "gl-135","gl-138","gl-139","gl-142","gl-143","gl-145","gl-149","gl-150","gl-152","gl-156","gl-157",
    "gl-160","gl-163","gl-164","gl-165",
    "gl-148","gl-154","gl-155","gl-158","gl-161","gl-166",
    "gl-133","gl-146","gl-151",
    "gl-186","gl-187",
    "gl-217","gl-218","gl-219","gl-220","gl-221","gl-222","gl-223","gl-224",
    "gl-225","gl-226","gl-228","gl-230","gl-231",
}
NUMPY_VERIFIED={"gl-098","gl-099","gl-100","gl-101","gl-102","gl-103","gl-104","gl-105","gl-106","gl-110","gl-111","gl-112","gl-113","gl-114","gl-115","gl-116","gl-117","gl-119","gl-120","gl-121","gl-122","gl-123","gl-124","gl-125","gl-127","gl-128","gl-129","gl-130","gl-131","gl-132"}
PANDAS_VERIFIED={"gl-133","gl-135","gl-137","gl-138","gl-139","gl-140","gl-141","gl-143","gl-144","gl-146","gl-150","gl-151","gl-152","gl-153","gl-154","gl-156","gl-157","gl-160","gl-163","gl-164","gl-165","gl-166"}
HARD_BLOCKERS={
    "gl-168":"Pinned urllib3 Emscripten adapter requires the browser-only js module, unavailable in CPython.",
    "gl-170":"A valid OpenSSL X509 certificate fixture is still required; an empty X509 object is rejected by ASN.1 conversion.",
    "gl-174":"create_connection requires a bounded local listening socket fixture; the no-network probe correctly received connection refused.",
    "gl-179":"ssl_wrap_socket requires a connected socket and matching local TLS server fixture.",
    "gl-118":"The normally installed NumPy source differs at this generated/build-time file, so the pristine patch cannot apply to the installed tree.",
    "gl-126":"The normally installed NumPy source differs at this generated/build-time file, so the pristine patch cannot apply to the installed tree.",
}
SKIP_NAMES={
 "networkx":{"asadpour_atsp","forceatlas2_layout","extended_barabasi_albert_graph","kernighan_lin_bisection","grid_2d_graph","spring_layout","asyn_fluidc","connected_double_edge_swap","scale_free_graph","view_pygraphviz","greedy_node_swap_bipartition","approximate_current_flow_betweenness_centrality","greedy_k_edge_augmentation","triad_type","asyn_lpa_communities"},
 "numpy":{"create_name_header","parse_loop_header","parse_signature","norm"},
 "pandas":{"json_normalize","array_ufunc","bootstrap_plot","concatenate_managers","sliding_min_max","sliding_var","sliding_mean","option_context","to_dict","flex_binary_moment","union_indexes","np_can_hold_element"},
 "urllib3":{"send_jspi_request","send_request","get_subj_alt_name","create_connection","ssl_wrap_socket","request"},
 "jsonschema":{"additionalItems","run","items_draft3_draft4","items_draft6_draft7_draft201909","patternProperties"},
 "packaging":{"platform_tags"},
 "attrs":{"pipe"},
}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def module_for(project, rel):
    parts=list(rel.with_suffix("").parts)
    if "src" in parts: parts=parts[parts.index("src")+1:]
    elif project == "networkx" and "networkx" in parts: parts=parts[parts.index("networkx"):]
    elif project == "requests" and "requests" in parts: parts=parts[parts.index("requests"):]
    elif project == "urllib3" and "src" in parts: parts=parts[parts.index("src")+1:]
    if parts[-1] == "__init__": parts=parts[:-1]
    return ".".join(parts)

def score(node):
    loops=sum(isinstance(n,(ast.For,ast.While,ast.comprehension)) for n in ast.walk(node))
    calls=sum(isinstance(n,ast.Call) for n in ast.walk(node))
    containers=sum(isinstance(n,(ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp,ast.Set,ast.Dict)) for n in ast.walk(node))
    return loops*12+containers*6+calls+(node.end_lineno-node.lineno)/8

def candidates(project, checkout):
    out=[]
    for path in checkout.rglob("*.py"):
        rel=path.relative_to(checkout)
        low=rel.as_posix().lower()
        parts=set(rel.parts)
        if parts & {"test","tests","examples","example","doc","docs","tools","scripts","tasks","dummyserver","f2py","_testing","code_generators"}: continue
        if any(x in low for x in ("/test", "bench", "vendor", "vendored", "_generated", "compat/", "noxfile.py", "prebuild.py", "testpypi_")): continue
        try: tree=ast.parse(path.read_bytes())
        except (SyntaxError,UnicodeDecodeError): continue
        for node in tree.body:
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
            if node.name.startswith("_") or node.end_lineno-node.lineno < 7: continue
            if node.name in SKIP_NAMES.get(project,set()): continue
            if project=="packaging" and node.name=="ios_platforms": continue
            if project=="networkx":
                positional=node.args.posonlyargs+node.args.args
                required=[a.arg for a in positional[:len(positional)-len(node.args.defaults)]]
                allowed={"G","G1","G2","H","graph","source","target","u","v","s","t","n","m","k","p","q","seed","weight","nodes","nbunch","create_using","degree_sequence","sequence"}
                if any(name not in allowed for name in required) or len(required)>4: continue
            s=score(node)
            if s < 8: continue
            out.append((s,rel,node.name,node.lineno,node.end_lineno))
    return sorted(out,key=lambda x:(-x[0],x[1].as_posix(),x[2]))

def marked_text(raw, node, case_id):
    tree=ast.parse(raw)
    lines=raw.splitlines(keepends=True)
    insert=1
    if tree.body and isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Constant) and isinstance(tree.body[0].value.value,str):
        insert=tree.body[0].end_lineno+1
    future_ends=[n.end_lineno for n in tree.body if isinstance(n,ast.ImportFrom) and n.module=="__future__"]
    if future_ends: insert=max(future_ends)+1
    lines.insert(insert-1,"import perfmark\n")
    shift=1 if insert <= node.lineno else 0
    original=ast.dump(ast.parse(raw))
    statements=node.body[1:] if isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str) else node.body
    # Prefer statements containing the data-dependent work while avoiding string
    # literal indentation changes. Validate exact AST restoration before accepting.
    statements=sorted(statements,key=lambda st:-score(st))
    for statement in statements:
        trial=lines.copy(); start=statement.lineno-1+shift; end=statement.end_lineno+shift
        original_line=lines[statement.lineno-1+shift]
        indent=original_line[:len(original_line)-len(original_line.lstrip())]
        unit="\t" if "\t" in indent else "    "
        trial.insert(start,indent+f'with perfmark.region("{case_id}"):\n')
        for i in range(start+1,end+1): trial[i]=unit+trial[i]
        try: parsed=ast.parse("".join(trial))
        except SyntaxError: continue
        class Strip(ast.NodeTransformer):
            def visit_Import(self,n):
                return None if len(n.names)==1 and n.names[0].name=="perfmark" else n
            def visit_With(self,n):
                expr=n.items[0].context_expr
                if isinstance(expr,ast.Call) and ast.unparse(expr.func)=="perfmark.region": return [self.visit(x) for x in n.body]
                return self.generic_visit(n)
        if ast.dump(Strip().visit(parsed))==original: return "".join(trial),statement.lineno,statement.end_lineno
    raise ValueError("no exactly restorable statement")

def arg_hints(name):
    n=name.lower()
    if n in {"g","g1","g2","graph","dg","h"} or "graph" in n: return ["make_graph()","make_graph(7)","make_graph(5,complete=True)"]
    if n in {"a","x","arr","array","values","data"} or "array" in n: return ["np.array([1,2,3])","np.arange(6).reshape(2,3)","np.array([3,1,2,1])"]
    if n in {"df","frame","obj"}: return ["pd.DataFrame({'a':[1,2],'b':[3,4]})","pd.Series([1,2,1])","pd.Index(['a','b','a'])"]
    if n in {"source","src","u","node","root"}: return ["0","0","1"]
    if n in {"target","dst","v"}: return ["3","4","2"]
    if n=="s": return ["0","0","1"]
    if n=="t": return ["3","4","2"]
    if n in {"n","k"}: return ["4","7","10"]
    if n=="m": return ["1","2","3"]
    if n in {"p","q"}: return ["0.2","0.5","0.8"]
    if n in {"seed","random_state"}: return ["random.Random(1)","random.Random(2)","random.Random(3)"]
    if n in {"weight"}: return ["None","'weight'","None"]
    if n in {"nodes","nbunch","sequence","degree_sequence"}: return ["[0,1]","[0,1,2]","[1,2,1,2]"]
    if n=="create_using": return ["nx.Graph","nx.DiGraph","nx.Graph"]
    if "schema" in n: return ["{'type':'integer'}","{'type':'array','items':{'type':'integer'}}","{'type':'object','properties':{'x':{'type':'number'}}}"]
    if n in {"instance","document"}: return ["1","[1,2,3]","{'x':2}"]
    if "path" in n or "file" in n or "url" in n: return ["'a/b/c.txt'","'alpha beta'","'/tmp/example.txt'"]
    if "version" in n: return ["'1.2.3'","'2.0rc1'","'0!1.0+local'"]
    if "name" in n or "key" in n or "text" in n or "string" in n or "pattern" in n: return ["'alpha'","'a/b/*.py'","'x-y_z'"]
    if "mapping" in n or "headers" in n or "dict" in n: return ["{}","{'a': 1}","{'a': 1, 'b': 2}"]
    if "iter" in n or "items" in n or "values" in n or "nodes" in n or "seq" in n: return ["[]","[1, 2]","[1, 2, 3, 4]"]
    if n.startswith("is_") or n in {"strict","validate","verify"}: return ["False","True","False"]
    return ["0","1","3"]

DRIVER=r'''"""Bounded correctness and marker-entry driver generated for {case_id}."""
import argparse, ast, importlib, inspect, json, re, sys, __future__, io, socket, random, math, http.client, tempfile
from email import message_from_string
from pathlib import Path
from marker_probe import Probe

CASE={case!r}
def stable(value):
    if inspect.isgenerator(value) or (hasattr(value,"__next__") and not isinstance(value,(str,bytes))): value=list(value)
    if hasattr(value,"tolist"): value=value.tolist()
    if isinstance(value,dict): return ("dict",sorted((stable(k),stable(v)) for k,v in value.items()))
    if isinstance(value,float) and math.isnan(value): return "NaN"
    if isinstance(value,(list,tuple)): return (type(value).__name__,tuple(stable(x) for x in value))
    if isinstance(value,(set,frozenset)): return (type(value).__name__,tuple(sorted(stable(x) for x in value)))
    if isinstance(value,(str,int,float,bool,bytes,type(None))): return value
    rendered=re.sub(r"(?: at 0x[0-9a-fA-F]+| @ [0-9]+)>",">",repr(value))
    return re.sub(r"_CountingAttr\(counter=\d+", "_CountingAttr(counter=*", rendered)

parser=argparse.ArgumentParser(); parser.add_argument("--source-root",required=True); args=parser.parse_args()
root=Path(args.source_root).resolve(); sys.path.insert(0,str(root/"src")); sys.path.insert(0,str(root))
probe=Probe()
try: import networkx as nx
except ImportError: nx=None
def make_graph(n=4,directed=False,complete=False):
    graph=(nx.complete_graph(n,create_using=nx.DiGraph) if complete and directed else
           nx.complete_graph(n) if complete else nx.path_graph(n,create_using=nx.DiGraph) if directed else nx.path_graph(n))
    nx.set_edge_attributes(graph,1,"weight")
    nx.set_edge_attributes(graph,1,"capacity")
    return graph
def make_data_file():
    f=tempfile.NamedTemporaryFile(mode="w",delete=False);f.write("1 2\n3 4\n");f.close();return f.name
try: import numpy as np
except ImportError: np=None
try: import pandas as pd
except ImportError: pd=None
try:
    import attr
    @attr.define
    class Sample:
        x:int=1
except ImportError: Sample=None
try:
    from pathspec import PathSpec
    ps=PathSpec.from_lines("gitwildmatch",["*.py","build/"])
except ImportError: ps=None
try:
    from requests import Response
    from requests.cookies import RequestsCookieJar
except ImportError: Response=RequestsCookieJar=None
try:
    from packaging.tags import Tag
    from packaging.version import Version
    from packaging._ranges import FULL_RANGE
except ImportError: Tag=Version=None
try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError
except ImportError: Draft202012Validator=ValidationError=None
try: from OpenSSL import crypto
except ImportError: crypto=None
module=importlib.import_module(CASE["module"])
loaded=Path(module.__file__).resolve()
assert loaded.is_relative_to(root), (loaded,root)
fn=getattr(module,CASE["symbol"])
sig=inspect.signature(fn)
# Compile the exact pristine upstream function in the imported module namespace.
# Clearing decorators avoids dispatch wrappers while preserving the body and globals.
original_tree=ast.parse((Path(__file__).with_name("original.py")).read_bytes())
original_node=next(n for n in original_tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==CASE["symbol"] and n.lineno==CASE["lineno"])
original_node.decorator_list=[]
namespace=dict(module.__dict__)
exec(compile(ast.fix_missing_locations(ast.Module(body=[original_node],type_ignores=[])),"<pinned-pristine>","exec",flags=__future__.annotations.compiler_flag),namespace)
baseline=namespace[CASE["symbol"]]
def invoke(target,variant):
    positional=[]; keywords={}
    for p in sig.parameters.values():
        if p.kind is p.VAR_KEYWORD: continue
        if p.kind is p.VAR_POSITIONAL:
            positional.extend(eval(CASE["args"].get(p.name,["[]"]*3)[variant],globals()));continue
        if p.default is not inspect.Parameter.empty and p.name not in CASE["force"]: continue
        value=eval(CASE["args"].get(p.name,["0","1","3"])[variant],globals())
        if p.kind is p.KEYWORD_ONLY: keywords[p.name]=value
        else: positional.append(value)
    return stable(target(*positional,**keywords))
outcomes=[]
for variant in range(3):
    expected=invoke(baseline,variant); actual=invoke(fn,variant)
    assert actual==expected, (variant,expected,actual)
    outcomes.append(actual)
assert len(outcomes)==3
probe.finish(CASE["id"])
'''

def main():
    cases=HERE/"cases"; upstream=HERE/"upstream"; support=HERE/"test-support"
    cases.mkdir(parents=True,exist_ok=True); upstream.mkdir(exist_ok=True); support.mkdir(exist_ok=True)
    shutil.copy2(HERE.parent/"support/marker_probe.py",support/"marker_probe.py")
    number=0
    for project,repo,revision,quota in REPOS:
        checkout=Path("/tmp")/f"drperf-gl-{project}"
        if not checkout.exists(): raise SystemExit(f"missing pinned checkout {checkout}")
        if __import__('subprocess').check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()!=revision: raise SystemExit(f"wrong revision: {project}")
        license=next((p for p in checkout.iterdir() if p.is_file() and p.name.upper().startswith(("LICENSE","COPYING"))),None)
        if license:
            d=upstream/project; d.mkdir(exist_ok=True); shutil.copy2(license,d/license.name)
        selected=candidates(project,checkout)
        accepted=0
        copied=set()
        for _s,rel,symbol,start,end in selected:
            if accepted >= quota: break
            cid=f"gl-{number+1:03d}"; src=checkout/rel
            snap=upstream/project/rel; snap.parent.mkdir(parents=True,exist_ok=True)
            if rel not in copied: shutil.copy2(src,snap); copied.add(rel)
            raw=src.read_text(); tree=ast.parse(raw); node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==symbol and n.lineno==start)
            try: marked,block_start,block_end=marked_text(raw,node,cid)
            except ValueError: continue
            number+=1; accepted+=1
            case=cases/cid; (case/"tests").mkdir(parents=True,exist_ok=True)
            patch="".join(difflib.unified_diff(raw.splitlines(True),marked.splitlines(True),fromfile=f"a/{rel.as_posix()}",tofile=f"b/{rel.as_posix()}"))
            (case/"region.patch").write_text(patch)
            mod=module_for(project,rel)
            params=[p.arg for p in node.args.posonlyargs+node.args.args+node.args.kwonlyargs]
            if node.args.vararg: params.append(node.args.vararg.arg)
            hints={p:arg_hints(p) for p in params}
            if project=="attrs":
                for p in params:
                    if p.lower() in {"inst","obj","cls"}: hints[p]=["Sample(1)","Sample(2)","Sample(3)"] if p.lower()!="cls" else ["Sample","Sample","Sample"]
            if project=="pathspec":
                for p in params:
                    if "pattern" in p.lower(): hints[p]=["ps.patterns","ps.patterns","ps.patterns"] if p.lower().endswith("s") else ["ps.patterns[0]","ps.patterns[1]","ps.patterns[0]"]
            overrides={
              "urllib3":{"url":["'http://example.com/a'","'https://example.org:8443/x?y=1'","'/relative/path'"],"hostname":["'example.com'"]*3,"cert":["{'subjectAltName':(('DNS','example.com'),)}"]*3,"fields":["{'a':'1'}","[('a','1'),('b','2')]","{'file':('x.txt',b'abc')}"],"body":["b'abc'","[b'a',b'b']","None"],"method":["'POST'","'PUT'","'GET'"],"blocksize":["16","8","32"],"address":["('localhost',9)"]*3,"headers":["http.client.parse_headers(io.BytesIO(b'A: b\\r\\n\\r\\n'))"]*3,"name":["'filename'"]*3,"value":["'x.txt'","'café.txt'","'a b'"],"sock":["socket.socket()"]*3,"fingerprint":["'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'"]*3},
              "requests":{"url":["'http://example.com/a'","'https://example.org/x'","'http://localhost/'"],"value":["'<a>; rel=next'","'text/plain; charset=utf-8'","'a=1, b=2'"],"cookie_dict":["{'a':'1'}","{'a':'1','b':'2'}","{}"],"cookiejar":["RequestsCookieJar()"]*3,"cookies":["{'a':'1'}","RequestsCookieJar()","{}"],"o":["io.BytesIO(b'abc')","b'abc'","'abc'"],"proxies":["{}","{'http':'http://proxy'}","{'all':'http://proxy'}"],"uri":["'a%20b'","'x%2Fy'","'plain'"],"hooks":["{}"]*3,"hook_data":["Response()"]*3},
              "packaging":{"tag":["'py3-none-any'","'cp312-abi3-manylinux_2_17_x86_64'","'py2.py3-none-any'"],"raw_license_expression":["'MIT'","'Apache-2.0 OR MIT'","'(MIT AND BSD-3-Clause)'"],"data":["'Name: demo\\nVersion: 1.0\\n'","b'Name: demo\\nVersion: 1.0\\n'","'Metadata-Version: 2.1\\nName: x\\nVersion: 2\\n'"],"tags":["[Tag('py3','none','any')]","[Tag('cp312','abi3','linux_x86_64')]","[]"],"archs":["['x86_64']","['aarch64']","['x86_64','i686']"],"dependency_groups":["{'test':['pytest']}" ]*3,"filename":["'demo-1.0-py3-none-any.whl'","'pkg-2.0-py2.py3-none-any.whl'","'demo-1.0.tar.gz'"],"op":["'>='","'=='","'~='"],"version":["Version('1.0')","Version('2.0')","Version('1.2')"],"has_local":["False","False","True"],"api_level":["21","28","34"],"abi":["'x86_64'","'arm64_v8a'","'x86'"],"name":["'Foo_Bar'","'hello.world'","'A--B'" ],"ranges":["FULL_RANGE"]*3,"region":["()"]*3,"iterable":["['0.9','1.0','2.0']"]*3,"key":["None"]*3,"prereleases":["None","False","True"],"left":["FULL_RANGE"]*3,"right":["FULL_RANGE"]*3},
              "attrs":{"attrs":["{'x':attr.ib()}","['x','y']","{'z':attr.ib(default=1)}"],"regex":["'a+'","'^x$'","'[0-9]+'"]},
              "pathspec":{"root":["'.'","'.'","'.'"],"file":["'a.py'","'build/x'","'readme.md'"]},
              "jsonschema":{"validator":["Draft202012Validator({'type':'object'})"]*3,"instance":["{'x':1}","{'x':'a'}","{'y':2}"],"schema":["{'properties':{'x':{'type':'integer'}}}","{'type':'object','additionalProperties':False}","{'items':{'type':'integer'}}"],"oneOf":["[{'type':'integer'},{'type':'string'}]"]*3,"errors":["[ValidationError('a'),ValidationError('b')]"]*3,"types":["'integer'","['integer','string']","'object'"],"unevaluatedProperties":["False"]*3,"uP":["False"]*3,"aI":["False"]*3,"dependencies":["{'x':['y']}"]*3,"container":["[1,2,1]","['a','b','a']","[{'x':1},{'x':1}]" ]},
            }
            for p in params:
                if p in overrides.get(project,{}): hints[p]=overrides[project][p]
            force=[]
            if (project,symbol) in {("urllib3","encode_multipart_formdata")}:
                hints["boundary"]=["'BOUNDARY'"]*3; force.append("boundary")
            if (project,symbol)==("urllib3","assert_fingerprint"): hints["cert"]=["b'abc'"]*3
            if (project,symbol)==("urllib3","match_hostname"):
                hints.update({"cert":["{'subject':((('commonName','example.com'),),)}"]*3,"hostname_checks_common_name":["True"]*3});force.append("hostname_checks_common_name")
            if (project,symbol)==("urllib3","get_subj_alt_name"): hints["peer_cert"]=["crypto.X509()"]*3
            if (project,symbol)==("urllib3","rewind_body"): hints.update({"body":["io.BytesIO(b'a')","io.BytesIO(b'abcd')","io.BytesIO(b'abcdefgh')"],"body_pos":["0"]*3})
            if (project,symbol)==("urllib3","poll_wait_for_socket"):
                hints.update({"sock":["socket.socket()"]*3,"read":["True"]*3});force.append("read")
            if (project,symbol)==("packaging","parse_wheel_filename"): hints["filename"]=["'demo-1.0-py3-none-any.whl'","'pkg-2.0-py2.py3-none-any.whl'","'x-1.2-cp312-abi3-linux_x86_64.whl'"]
            if (project,symbol)==("packaging","parse_sdist_filename"): hints["filename"]=["'demo-1.0.tar.gz'","'pkg-2.0.zip'","'x-1.2.tar.gz'"]
            if (project,symbol)==("packaging","android_platforms"): force.extend(["api_level","abi"])
            if (project,symbol)==("packaging","mac_platforms"):
                hints.update({"version":["(13,0)","(12,6)","(11,0)"],"arch":["'x86_64'","'arm64'","'x86_64'"]});force.extend(["version","arch"])
            if (project,symbol)==("packaging","intersect_specifier_bounds"):
                hints["per_specifier_ranges"]=["[FULL_RANGE]","[FULL_RANGE,FULL_RANGE]","[FULL_RANGE,FULL_RANGE,FULL_RANGE]"]
            if (project,symbol)==("packaging","resolve_dependency_groups"):
                hints["groups"]=["['test']","['test','test']","['test']"]
            if (project,symbol)==("pathspec","check_match_file"): hints["patterns"]=["list(enumerate(ps.patterns))"]*3
            if (project,symbol)==("requests","should_bypass_proxies"):
                hints["no_proxy"]=["'localhost'","'example.org'","''"];force.append("no_proxy")
            if (project,symbol)==("requests","merge_setting"):
                hints.update({"request_setting":["{'a':1}","{'a':2}","{}"],"session_setting":["{'b':2}","{'a':1}","{'c':3}"]})
            if (project,symbol)==("requests","cookiejar_from_dict"):
                hints["cookiejar"]=["RequestsCookieJar()"]*3;force.append("cookiejar")
            if project=="pandas":
                pandas_hints={
                  "into":["dict"]*3,"data":["pd.DataFrame({'a':[1,2],'b':[3,4]})"]*3,
                  "obj":["[1,2,3]","[1,2]","[3,1,2]"],"formatter":["str"]*3,
                  "frame":["pd.DataFrame({'a':[1,2],'b':[3,4]})"]*3,"objs":["[pd.DataFrame({'a':[1]}),pd.DataFrame({'a':[2]})]"]*3,
                  "columns":["pd.Index(['a','b'])"]*3,"index":["pd.RangeIndex(2)"]*3,
                  "comps":["[1,2,3]"]*3,"values":["[2,4]","[1]","[3,5]"],
                  "types":["[np.dtype('int64'),np.dtype('float64')]"]*3,"groups":["{'x':['a'],'y':['b']}"]*3,
                  "to_concat":["[np.array([1,2]),np.array([3,4])]"]*3,
                  "labels":["[np.array([0,1,0]),np.array([0,0,1])]"]*3,"shape":["(2,2)"]*3,
                  "source":["'D'","'M'","'Q'"],"target":["'h'","'D'","'M'"],
                  "to_union":["[pd.Categorical(['a','b']),pd.Categorical(['b','c'])]"]*3,
                }
                for p in params:
                    if p in pandas_hints:hints[p]=pandas_hints[p]
                if symbol=="read_csv": hints["filepath_or_buffer"]=["io.StringIO('a,b\\n1,2\\n3,4\\n')","io.StringIO('a,b\\n1,2\\n3,4\\n5,6\\n7,8\\n')","io.StringIO('a,b\\n1,2\\n3,4\\n5,6\\n7,8\\n9,10\\n11,12\\n13,14\\n15,16\\n')"]
                if symbol=="to_dict": force.append("into")
                if symbol=="to_dict": hints["df"]=["pd.DataFrame({'a':[1,2]})","pd.DataFrame({'a':[1,2],'b':[3,4]})","pd.DataFrame(index=[0,1])"]
                if symbol=="json_normalize": hints["data"]=["[{'a':1}]","[{'a':1},{'a':2}]","{'a':{'b':1}}"]
                if symbol=="get_grouper": hints["obj"]=["pd.Series([1,2,1])"]*3
                if symbol=="ndarray_to_mgr": hints["values"]=["np.array([[1,2],[3,4]])"]*3
                if symbol=="radviz": hints.update({"frame":["pd.DataFrame({'x':[1,2],'y':[3,4],'cls':['a','b']})"]*3,"class_column":["'cls'"]*3})
                if symbol=="bootstrap_plot": hints["series"]=["pd.Series(range(20))"]*3
                if symbol=="dict_to_mgr": hints["data"]=["{'a':[1,2],'b':[3,4]}"]*3
                if symbol=="array_ufunc": hints.update({"self":["pd.Series([1,2,3])"]*3,"ufunc":["np.add"]*3,"method":["'__call__'"]*3})
                if symbol=="to_arrays": hints.update({"data":["[{'a':1,'b':2},{'a':3,'b':4}]"]*3,"columns":["pd.Index(['a','b'])"]*3})
                if symbol=="get_grouper": hints.update({"obj":["pd.Series([1,2,1])"]*3,"key":["lambda x: x % 2"]*3});force.append("key")
                if symbol=="ndarray_to_mgr": hints.update({"dtype":["np.dtype('int64')"]*3,"copy":["False","True","False"]})
                if symbol=="bootstrap_plot": hints.update({"size":["5"]*3,"samples":["3"]*3});force.extend(["size","samples"])
                if symbol=="sliding_min_max": hints.update({"values":["np.array([3.,1.,2.,4.])"]*3,"result_dtype":["np.dtype('float64')"]*3,"start":["np.array([0,0,1,2],dtype=np.int64)"]*3,"end":["np.array([1,2,3,4],dtype=np.int64)"]*3,"min_periods":["1"]*3,"is_max":["False","True","False"]})
                if symbol=="option_context": hints["args"]=["['display.max_rows',10]","['display.max_columns',5]","['mode.copy_on_write',False]"]
                if symbol=="get_handle": hints.update({"path_or_buf":["io.BytesIO(b'a')","io.BytesIO(b'ab')","io.BytesIO(b'abc')"],"mode":["'rb'"]*3,"is_text":["False"]*3});force.append("is_text")
                if symbol=="pivot": hints.update({"data":["pd.DataFrame({'i':[1,2],'c':['a','b'],'v':[3,4]})","pd.DataFrame({'i':[1,2,3],'c':['a','b','c'],'v':[3,4,5]})","pd.DataFrame({'i':[1,2,3,4],'c':['a','b','a','b'],'v':[3,4,5,6]})"],"columns":["'c'"]*3})
                if symbol=="from_dummies": hints["data"]=["pd.DataFrame({'a':[1,0],'b':[0,1]})","pd.DataFrame({'a':[1,0,1],'b':[0,1,0]})","pd.DataFrame({'a':[0,1],'b':[1,0]})"]
                if symbol=="isin": hints.update({"comps":["pd.Series([1,2])","pd.Series([1,2,3,4])","pd.Series([1,2,3,4,5,6,7,8])"],"values":["[2]","[1,3]","[3,5,7]"]})
                if symbol=="hash_pandas_object": hints["obj"]=["pd.Series([1,2])","pd.Index(['a','b','c','d'])","pd.DataFrame({'a':range(8)})"]
                if symbol=="array": hints["data"]=["[1,2]","['a','b','c','d']","list(range(8))"]
                if symbol=="stack_multiple": hints["level"]=["[0]","[0]","[0]"]
                if symbol=="stack_v3": hints.update({"frame":["pd.DataFrame([[1,2,3],[4,5,6]],columns=pd.MultiIndex.from_tuples([('A','u'),('A','v'),('B','u')]))","pd.DataFrame([[1,2,3],[4,5,6]],columns=pd.MultiIndex.from_tuples([('A','u'),('A','v'),('B','u')]))","pd.DataFrame([[1,2,3,4]],columns=pd.MultiIndex.from_product([['A','B'],['u','v']]))"],"level":["[0]","[1]","[0,1]"]})
                if symbol in {"sliding_var","sliding_mean"}:
                    hints.update({"values":["np.array([1.,2.,3.,4.])","np.array([1.,np.nan,3.,5.,7.])","np.array([-2.,-2.,4.,8.,8.,1.])"],"result_dtype":["np.dtype('float64')","np.dtype('float64')","np.dtype('float32')"],"start":["np.array([0,0,1,2],dtype=np.int64)","np.array([0,1,0],dtype=np.int64)","np.array([0,2,1,4],dtype=np.int64)"],"end":["np.array([1,2,3,4],dtype=np.int64)","np.array([2,4,5],dtype=np.int64)","np.array([2,4,5,6],dtype=np.int64)"],"min_periods":["1","2","1"]})
                    if symbol=="sliding_var": hints["ddof"]=["1","0","1"];force.append("ddof")
                if symbol=="get_join_indexers": hints.update({"left_keys":["[np.array([1,2,3])]" ]*3,"right_keys":["[np.array([2,3,4])]" ]*3})
                if symbol=="select": hints.update({"df":["pd.DataFrame({'a':[1,2],'b':[3,4]})"]*3,"select_args":["('a',)"]*3,"select_kwargs":["{}"]*3})
                if symbol=="interval_range":
                    hints.update({"start":["0","pd.Timestamp('2020-01-01')","None"],"end":["4","None","10"],"periods":["None","3","4"],"freq":["1","'2D'","2"],"name":["None","'days'","None"],"closed":["'right'","'right'","'both'"]});force.extend(["start","end","periods","freq","name","closed"])
                if symbol=="wide_to_long": hints.update({"df":["pd.DataFrame({'id':[1,2],'A1970':[3,4],'A1980':[5,6]})","pd.DataFrame({'id':[1,2,3],'A1':[3,4,5],'A2':[5,6,7]})","pd.DataFrame({'id':[1,2],'A1':[3,4],'A2':[5,6],'B1':[7,8],'B2':[9,10]})"],"stubnames":["['A']","['A']","['A','B']"],"i":["'id'"]*3,"j":["'year'"]*3})
            if project=="numpy":
                structured="np.array([(1,2.0),(3,4.0)],dtype=[('a','i4'),('b','f8')])"
                numpy_hints={"a":["np.array([1,2,3])"]*3,"b":["np.array([4,5,6])"]*3,"axes":["1"]*3,"arr":[structured]*3,"r1":[structured]*3,"r2":[structured]*3,"arrays":["["+structured+"]"]*3,"seqarrays":["[np.array([1,2]),np.array([3,4])]"]*3,"func1d":["np.sum"]*3,"axis":["0"]*3,"sample":["np.array([[0.,1.],[1.,2.],[2.,3.]])"]*3,"alist":["[1,2,3]"]*3,"base":[structured]*3,"newfield":["np.array([5,6])"]*3,"condlist":["[np.array([True,False]),np.array([False,True])]" ]*3,"choicelist":["[np.array([1,1]),np.array([2,2])]" ]*3,"obj":["0","1","-1"],"x":["np.array([1,2,3,4])"]*3,"window_shape":["2","3","2"]}
                for p in params:
                    if p in numpy_hints:hints[p]=numpy_hints[p]
                if symbol=="tensordot": force.append("axes")
                if symbol in {"einsum_path","einsum"}: hints["operands"]=["['ij,jk->ik',np.ones((2,2)),np.ones((2,2))]"]*3
                if symbol=="meshgrid": hints["xi"]=["[np.arange(2),np.arange(3)]","[np.arange(3),np.arange(4),np.arange(2)]","[np.linspace(0,1,5),np.arange(2)]"]
                if symbol=="genfromtxt": hints["fname"]=["io.StringIO('1 2\\n3 4\\n')","io.StringIO('1 2\\n3 4\\n5 6\\n7 8\\n')","io.StringIO('1 2\\n3 4\\n5 6\\n7 8\\n9 10\\n11 12\\n13 14\\n15 16\\n')"]
                if symbol=="savetxt": hints.update({"fname":["io.StringIO()"]*3,"X":["np.array([[1,2],[3,4]])"]*3})
                if symbol=="join_by": hints["key"]=["'a'"]*3
                if symbol=="stack_arrays": hints["arrays"]=["["+structured+","+structured+"]"]*3
                if symbol=="gradient": hints["varargs"]=["[1.0]","[2.0]","[0.5]"]
                if symbol=="apply_along_axis": hints["args"]=["[]"]*3
                if symbol=="einsum": hints["optimize"]=["'greedy'"]*3;force.append("optimize")
                if symbol=="flatten_structured_array": hints["a"]=[structured]*3
                if symbol=="append_fields": hints.update({"names":["'c'"]*3,"data":["np.array([5,6])"]*3})
                if symbol=="addfield": hints.update({"mrecord":["np.ma.mrecords.fromarrays([[1,2],[3,4]],names='a,b')"]*3,"newfield":["np.array([5,6])"]*3})
                if symbol=="unstructured_to_structured": hints["arr"]=["np.array([[1,2.],[3,4.]])"]*3
                if symbol=="apply_along_axis": hints["arr"]=["np.array([[1,2],[3,4]])"]*3
                if symbol=="fromtextfile": hints["fname"]=["make_data_file()"]*3
                if symbol=="insert": hints.update({"arr":["np.array([1,2])","np.array([1,2,3,4])","np.arange(8)"],"obj":["1","2","4"],"values":["np.array([9])","np.array([8,9])","np.array([7])"]})
            if project=="jsonschema":
                if symbol=="contains": hints.update({"contains":["{'type':'integer'}"]*3,"instance":["[1,'x']","[1,2,'x']","['x',3,4,5]"]})
                if symbol=="unevaluatedItems": hints.update({"unevaluatedItems":["False"]*3,"instance":["[1,'x']","[1,2,'x']","['x',3,4,5]"]})
            if project=="networkx":
                if "seed" in params: force.append("seed")
                if symbol=="effective_size" and "nodes" in params: force.append("nodes")
                directed={"network_simplex","capacity_scaling","triadic_census","asadpour_atsp","recursive_simple_cycles","scale_free_graph","trophic_levels","all_topological_sorts","is_reachable","tree_all_pairs_lowest_common_ancestor","lexicographical_topological_sort"}
                bipartite={"eppstein_matching","hopcroft_karp_matching"}
                if symbol in directed:
                    for p in params:
                        if p in {"G","G1","G2","H","graph"}: hints[p]=["make_graph(4,True)","make_graph(7,True)","make_graph(5,True,True)"]
                if symbol in bipartite:
                    for p in params:
                        if p in {"G","G1","G2","H","graph"}: hints[p]=["nx.complete_bipartite_graph(2,2)","nx.complete_bipartite_graph(3,4)","nx.complete_bipartite_graph(2,3)"]
                if symbol in {"held_karp_ascent","asadpour_atsp"} and "G" in params: hints["G"]=["make_graph(4,True,True)","make_graph(5,True,True)","make_graph(6,True,True)"]
                if symbol=="k_factor": hints.update({"G":["make_graph(4,complete=True)","make_graph(6,complete=True)","make_graph(8,complete=True)"],"k":["2","2","2"]})
                if symbol=="intersection_array": hints["G"]=["nx.cycle_graph(4)","nx.cycle_graph(5)","nx.hypercube_graph(3)"]
                if symbol in {"all_topological_sorts","lexicographical_topological_sort"}: hints["G"]=["make_graph(4,True)","make_graph(7,True)","make_graph(5,True)"]
                if symbol=="find_cycle": hints["G"]=["nx.cycle_graph(4)","nx.cycle_graph(7)","nx.complete_graph(5)"]
                if symbol in {"tree_broadcast_center","tree_all_pairs_lowest_common_ancestor"}: hints["G"]=["nx.path_graph(4)","nx.balanced_tree(2,2)","nx.path_graph(7)"]
                if symbol=="tree_all_pairs_lowest_common_ancestor": hints["G"]=["nx.bfs_tree(nx.path_graph(4),0)","nx.bfs_tree(nx.balanced_tree(2,2),0)","nx.bfs_tree(nx.path_graph(7),0)"]
                if symbol=="complete_to_chordal_graph": hints["G"]=["nx.cycle_graph(4)","nx.cycle_graph(5)","nx.grid_2d_graph(2,3)"]
                if symbol=="maximal_extendability": hints["G"]=["nx.complete_graph(4)","nx.complete_graph(5)","nx.complete_graph(6)"]
                if symbol=="trophic_levels": hints["G"]=["make_graph(4,True)","make_graph(7,True)","make_graph(5,True)"]
                if symbol=="geometric_soft_configuration_graph": hints["beta"]=["1.0","2.0","3.0"]
                if symbol=="prominent_group": hints["k"]=["1","2","2"]
                if symbol=="maximal_extendability": hints["G"]=["nx.complete_bipartite_graph(2,2)","nx.complete_bipartite_graph(3,3)","nx.complete_bipartite_graph(4,4)"]
                if symbol=="geometric_soft_configuration_graph":
                    hints.update({"n":["10","12","15"],"gamma":["2.5","3.0","3.5"],"mean_degree":["2.0","3.0","4.0"]});force.extend(["n","gamma","mean_degree"])
                if symbol in {"panther_vector_similarity","arf_layout","approximate_current_flow_betweenness_centrality"}: hints["seed"]=["np.random.RandomState(1)","np.random.RandomState(2)","np.random.RandomState(3)"]
                if symbol=="panther_vector_similarity":
                    hints.update({"k":["2","3","2"],"D":["2","3","4"]});force.extend(["k","D"])
                if symbol=="generate_edgelist": hints["G"]=["nx.complete_bipartite_graph(2,2)","nx.complete_bipartite_graph(3,4)","nx.complete_bipartite_graph(4,4)"]
                if symbol=="rich_club_coefficient": hints["normalized"]=["False"]*3;force.append("normalized")
                if symbol=="triad_type": hints["G"]=["nx.DiGraph([(0,1)])","nx.DiGraph([(0,1),(1,2)])","nx.DiGraph([(0,1),(1,2),(2,0)])"]
                if symbol=="magnetic_laplacian_matrix": hints["G"]=["make_graph(4,True)","make_graph(7,True)","make_graph(5,True)"]
                if symbol=="asyn_lpa_communities": hints["seed"]=["random.Random(1)","random.Random(2)","random.Random(3)"]
            positional=node.args.posonlyargs+node.args.args
            required={a.arg for a in positional[:len(positional)-len(node.args.defaults)]}
            required.update(a.arg for a,d in zip(node.args.kwonlyargs,node.args.kw_defaults) if d is None)
            if node.args.vararg: required.add(node.args.vararg.arg)
            used=required|set(force)
            hints={name:value for name,value in hints.items() if name in used}
            spec={"id":cid,"module":mod,"symbol":symbol,"lineno":start,"args":hints,"force":force}
            driver=DRIVER.replace("{case_id}",cid).replace("{case!r}",repr(spec))
            (case/"tests/test_case.py").write_text(driver)
            manifest={"schema_version":1,"id":cid,"title":f"Selected block in {project}.{symbol}","language":"python","source":{"repository":repo,"revision":revision,"path":rel.as_posix(),"snapshot":f"../../upstream/{project}/{rel.as_posix()}","sha256":sha(src)},"region":{"symbol":symbol,"start_line":block_start,"end_line":block_end,"kind":"block"},"marker":{"kind":"python-context","name":cid,"pcvs":[]},"status":"collected","build_status":"not-built","workload":{"description":f"Exercise {symbol} with three small, varied domain inputs; fully consume lazy results and compare values with the pinned pristine function.","command":["{python}","tests/test_case.py","--source-root","{source_root}"]},"source_family":f"{project}:{rel.as_posix()}:{symbol}","citations":[f"{repo}/blob/{revision}/{rel.as_posix()}"],"tests":{"files":["tests/test_case.py"],"resources":[{"source":"../../test-support/marker_probe.py","destination":"tests/marker_probe.py","sha256":sha(support/"marker_probe.py")},{"source":f"../../upstream/{project}/{rel.as_posix()}","destination":"tests/original.py","sha256":sha(src)}],"command":["{python}","tests/test_case.py","--source-root","{source_root}"],"validation":{"status":"not-run","details":"Concrete offline differential driver is present. It checks the imported module is inside the supplied pinned checkout, executes three bounded domain-input variants against both the marked target and the exact hashed pristine function, fully consumes lazy results, compares normalized returned values, and requires entry into the named marker. Matching dependency environments have not yet been run."},"coverage_note":f"Differentially calls {mod}.{symbol} on three bounded domain variants, consumes lazy outputs, compares with the pinned pristine function, and requires marker entry. The pristine body runs in a copied module namespace; recursive calls made through module globals may resolve to the imported marked symbol, so direct body equality is covered more strongly than recursive isolation."}}
            verified=False  # Promotion is receipt-driven after all files are written.
            if verified:
                environment="an isolated installed package tree built from the pinned revision" if project in {"numpy","pandas"} else "an isolated hard-linked checkout at the pinned revision"
                manifest["tests"]["validation"]={"status":"region-verified","details":f"Passed in {environment} under Python 3.12. The differential assertions matched the pristine function on three bounded variants, lazy results were consumed, the loaded module path was verified inside the patched source root, and the marker probe observed three entries. This is correctness and reachability evidence, not a performance measurement."}
            else:
                reason=HARD_BLOCKERS.get(cid,"The isolated Python 3.12 execution reached a target-specific input precondition or did not enter the selected statement; the fixture still requires specialization before region verification.")
                manifest["tests"]["validation"]={"status":"not-run","details":reason}
            (case/"case.json").write_text(json.dumps(manifest,indent=2)+"\n")
            (case/"task.md").write_text(f"# Investigate a block in `{symbol}`\n\nAnalyze the selected marked statement block within `{symbol}` in `{rel}`. Use bounded inputs that vary collection size or structure, preserve return values and exception behavior, and identify performance-critical variables only from measurements or source-supported cost reasoning.\n")
            (case/"reference.md").write_text(f"# Selection evidence\n\nSource: [{repo} at `{revision}`]({repo}/blob/{revision}/{rel.as_posix()}#L{block_start}-L{block_end}). The pristine snapshot is retained with its SHA-256 in `case.json`.\n\nThe selected statement contains iteration, comprehension, sorting, calls, or container construction and was selected as a plausible data-dependent optimization target. Potential opportunities include eliminating redundant traversal, intermediate allocation, repeated conversion, or avoidable membership work where profiling confirms it. No speedup or ground-truth optimization is asserted.\n")
        if accepted < quota: raise SystemExit(f"only {accepted} restorable candidates for {project}")
    # Promote only executions whose saved patch and driver hashes match the
    # files just generated and whose observer recorded this exact marker.
    for receipt_path in (HERE/"validation-executions").glob("*.json") if (HERE/"validation-executions").exists() else ():
        for execution in json.loads(receipt_path.read_text()).get("results",[]):
            cid=execution["id"]; case_dir=cases/cid
            if not case_dir.exists() or execution.get("returncode")!=0 or execution.get("marker_hits",{}).get(cid,0)<=0: continue
            if execution.get("patch_sha256")!=sha(case_dir/"region.patch") or execution.get("test_sha256")!=sha(case_dir/"tests/test_case.py"): continue
            manifest_path=case_dir/"case.json"; data=json.loads(manifest_path.read_text())
            data["tests"]["validation"]={"status":"region-verified","details":f"Receipt-bound execution passed under {execution.get('python','Python 3.12')}. The saved return code is zero, the observer recorded {execution['marker_hits'][cid]} marker entries, and receipt patch/test hashes match this case. Differential value assertions passed; this is not a performance measurement."}
            manifest_path.write_text(json.dumps(data,indent=2)+"\n")
    results=[]
    for manifest_path in sorted(cases.glob("*/case.json")):
        data=json.loads(manifest_path.read_text()); case_dir=manifest_path.parent
        assets={name:sha(case_dir/name) for name in data["tests"]["files"]}
        assets.update({r["destination"]:r["sha256"] for r in data["tests"]["resources"]})
        results.append({"id":data["id"],"repository":data["source"]["repository"],"revision":data["source"]["revision"],"path":data["source"]["path"],"region":data["region"],"source_sha256":data["source"]["sha256"],"patch_sha256":sha(case_dir/"region.patch"),"test_sha256":assets,"status":data["tests"]["validation"]["status"],"details":data["tests"]["validation"]["details"]})
    (HERE/"validation-results.json").write_text(json.dumps({"schema_version":1,"runner":"run_sweep.py","results":results},indent=2)+"\n")
    print(f"generated {number} cases")

if __name__ == "__main__": main()
