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
    spec.loader.exec_module(module)
    return module


before = load("aq003_before", case.parent.parent.parent / "bench_anontated" / "accidental-quadratic" / "aq-003" / "_baseline" / "Lib/http/cookies.py")
after = load("aq003_after", case / "Lib/http/cookies.py")
mismatches = []
checked = 0


def outcome(function, value):
    try:
        return ("ok", function(value))
    except Exception as exc:
        return ("error", type(exc).__name__, str(exc))


def check(value):
    global checked
    checked += 1
    left, right = outcome(before._unquote, value), outcome(after._unquote, value)
    if left != right:
        mismatches.append({"input": repr(value), "before": repr(left), "after": repr(right)})


alphabet = 'a\\"047'
for length in range(7):
    for chars in itertools.product(alphabet, repeat=length):
        check('"' + ''.join(chars) + '"')
rng = random.Random(0)
for _ in range(10_000):
    check('"' + ''.join(rng.choice(alphabet) for _ in range(rng.randrange(80))) + '"')
check(None)
check("plain")
result = {"seed": 0, "alphabet": alphabet, "checked": checked,
          "mismatch_count": len(mismatches), "mismatches": mismatches[:20]}
print(json.dumps(result, indent=2))
raise SystemExit(bool(mismatches))
