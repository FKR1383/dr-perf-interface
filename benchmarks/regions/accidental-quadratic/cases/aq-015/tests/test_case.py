#!/usr/bin/env python3
import argparse
import importlib.util
import os
import pathlib
import sys
from marker_probe import Probe

CASE_ID = 'aq-015'
SOURCE_PATH = 'Lib/email/_header_value_parser.py'
MODULE_NAME = 'email._aq_header_value_parser'
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
    token = module.parse_mime_version(f"{size}.{size + 1}")
    assert token.major == size and token.minor == size + 1 and not token.defects
invalid = module.parse_mime_version("1.x")
assert invalid.defects
probe.finish(CASE_ID)
print(f"{CASE_ID}: loaded {source_file} and reached parse_mime_version")
