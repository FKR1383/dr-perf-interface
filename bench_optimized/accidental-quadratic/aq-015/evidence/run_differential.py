#!/usr/bin/env python3
import contextlib
import importlib.util
import itertools
import json
import random
import sys
import types
from pathlib import Path


@contextlib.contextmanager
def region(*args, **kwargs):
    yield


perfmark = types.ModuleType("perfmark")
perfmark.region = region
sys.modules["perfmark"] = perfmark
case = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


before = load("email._aq015_before", case.parent.parent.parent / "bench_anontated" / "accidental-quadratic" / "aq-015" / "_baseline" / "Lib/email/_header_value_parser.py")
after = load("email._aq015_after", case / "Lib/email/_header_value_parser.py")
mismatches = []
checked = 0


def outcome(function, value):
    try:
        token = function(value)
        defects = [type(item).__name__ + ":" + str(item) for item in token.defects]
        return ("ok", str(token), token.major, token.minor, defects)
    except Exception as exc:
        return ("error", type(exc).__name__, str(exc))


def check(value):
    global checked
    checked += 1
    left, right = outcome(before.parse_mime_version, value), outcome(after.parse_mime_version, value)
    if left != right:
        mismatches.append({"input": repr(value), "before": repr(left), "after": repr(right)})


alphabet = "01.x "
for length in range(7):
    for chars in itertools.product(alphabet, repeat=length):
        check(''.join(chars))
rng = random.Random(15)
for _ in range(20_000):
    check(''.join(rng.choice(alphabet) for _ in range(rng.randrange(80))))
result = {"seed": 15, "alphabet": alphabet, "checked": checked,
          "mismatch_count": len(mismatches), "mismatches": mismatches[:20]}
print(json.dumps(result, indent=2))
raise SystemExit(bool(mismatches))
