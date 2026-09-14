#!/usr/bin/env python3
import argparse
import importlib.util
import os
import pathlib
import sys
from marker_probe import Probe

CASE_ID = 'aq-003'
SOURCE_PATH = 'Lib/http/cookies.py'
MODULE_NAME = '_aq_aq_003'
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

for size in (1, 2, 4, 8, 16):
    encoded = '"' + (r"a\042" * size) + '"'
    assert module._unquote(encoded) == ('a"' * size)
assert module._unquote("plain") == "plain"
probe.finish(CASE_ID)
print(f"{CASE_ID}: loaded {source_file} and reached _unquote")
