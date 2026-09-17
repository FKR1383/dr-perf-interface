#!/usr/bin/env python3
import argparse
import importlib.util
import os
import pathlib
import sys
from marker_probe import Probe

CASE_ID = 'aq-002'
SOURCE_PATH = 'Cython/Compiler/ModuleNode.py'
MODULE_NAME = 'Cython.Compiler._aq_ModuleNode'
probe = Probe()

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True)
args = parser.parse_args()
source_root = pathlib.Path(args.source_root).resolve()
source_file = (source_root / SOURCE_PATH).resolve()
assert source_file.is_file(), source_file
for entry in (source_root, source_root / "src"):
    sys.path.insert(0, str(entry))
spec = importlib.util.spec_from_file_location(MODULE_NAME, source_file)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)
assert pathlib.Path(module.__file__).resolve() == source_file

class Type:
    def __init__(self, key, base=None): self.key, self.base_type = key, base
class Entry:
    def __init__(self, key, base=None): self.type, self.base_keys = Type(key, base), set()
for size in (1, 2, 4, 8, 16):
    base = Entry(f"base{size}")
    children = [Entry(f"child{i}", base.type) for i in range(size)]
    entries = {x.type.key: x for x in [base, *children]}
    order = [x.type.key for x in children] + [base.type.key]
    out = module.ModuleNode.sort_types_by_inheritance(object(), entries, order, lambda typ: typ.key)
    assert out[0] is base and len(out) == size + 1
probe.finish(CASE_ID)
print(f"{CASE_ID}: loaded {source_file} and reached ModuleNode.sort_types_by_inheritance")
