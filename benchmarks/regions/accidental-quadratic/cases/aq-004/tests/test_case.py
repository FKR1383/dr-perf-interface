#!/usr/bin/env python3
import argparse
import importlib.util
import os
import pathlib
import sys
from marker_probe import Probe

CASE_ID = 'aq-004'
SOURCE_PATH = 'Lib/html/parser.py'
MODULE_NAME = '_aq_aq_004'
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

events = []
class Parser(module.HTMLParser):
    def handle_data(self, data): events.append(data)
for size in (1, 2, 4, 8, 16):
    p = Parser(); p.feed("<a " * size); p.close()
    assert p.rawdata == ""
complete = Parser(); complete.feed("<p>x</p>" * 4); complete.close()
assert complete.rawdata == ""
probe.finish(CASE_ID)
print(f"{CASE_ID}: loaded {source_file} and reached HTMLParser.goahead")
