#!/usr/bin/env python3
import argparse
import contextlib
import importlib.util
import os
import pathlib
import sys
import types
from marker_probe import Probe

CASE_ID = 'aq-009'
SOURCE_PATH = 'src/black/linegen.py'
MODULE_NAME = 'black._aq_linegen'
@contextlib.contextmanager
def _unmeasured_region(name, **pcvs):
    yield

_real_perfmark = None
_real_region = None
if os.environ.get("DRPERF"):
    import perfmark as _real_perfmark
    _real_region = _real_perfmark.region
    _real_perfmark.region = _unmeasured_region
else:
    _unmeasured = types.ModuleType("perfmark")
    _unmeasured.region = _unmeasured_region
    sys.modules["perfmark"] = _unmeasured

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

def run_matrix():
    import black
    for size in (1, 2, 4, 8, 16):
        source = "value = " + "+".join(f"({i})" for i in range(size)) + "\n"
        result = black.format_str(source, mode=black.Mode())
        assert "value" in result and result.endswith("\n")

run_matrix()  # specialize and populate caches before DrPerf attaches
if _real_perfmark is not None:
    _real_perfmark.region = _real_region
probe = Probe()
module.perfmark = sys.modules["perfmark"]
run_matrix()
probe.finish(CASE_ID)
print(f"{CASE_ID}: loaded {source_file} and reached normalize_invisible_parens")
