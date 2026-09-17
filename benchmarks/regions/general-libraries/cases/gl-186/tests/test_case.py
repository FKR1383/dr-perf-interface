"""Bounded correctness and marker-entry driver generated for gl-186."""
import argparse, ast, importlib, inspect, json, re, sys, __future__, io, socket, random, math, http.client, tempfile
from email import message_from_string
from pathlib import Path
from marker_probe import Probe

CASE={'id': 'gl-186', 'module': 'requests.sessions', 'symbol': 'merge_setting', 'lineno': 76, 'args': {'request_setting': ["{'a':1}", "{'a':2}", '{}'], 'session_setting': ["{'b':2}", "{'a':1}", "{'c':3}"]}, 'force': []}
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
