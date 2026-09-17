"""End-to-end marker/reader regressions; requires ./build.sh and DynamoRIO."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import derive
import runner

COUNTS = (0, 1, 4, 6, 8, 9, 16, 64)
BASE = 1 << 54  # reader must preserve integers beyond float's exact range


def python_worker(mode):
    if mode == "ctypes":
        os.environ["PERFMARK_NO_EXT"] = "1"
    sys.path.insert(0, str(ROOT / "perfmark/python"))
    import perfmark
    assert perfmark.available and perfmark.fast == (mode == "fast")
    for n in COUNTS:
        for _ in range(2):
            for variant in range(3):
                values = {f"pcv_{j}": BASE+j+(variant if j == n-1 else 0) for j in range(n)}
                with perfmark.region(f"pcvs_{n}", **values, note="extra", enabled=True):
                    pass
    for value in (-(1 << 63)-1, 1 << 63):
        try:
            perfmark.region("invalid_int", value=value)
        except OverflowError:
            pass
        else:
            raise AssertionError("out-of-range PCV was silently converted")
    if mode == "fast":
        # Also test callers using the low-level extension directly.
        for n in (1, 64):
            pairs = [(f"pcv_{j}".encode(), 1 << 100 if j == n-1 else j) for j in range(n)]
            try:
                perfmark._ext.Region(b"invalid_direct", pairs, None).__enter__()
            except OverflowError:
                pass
            else:
                raise AssertionError("extension opened a region after failed integer conversion")
    print(f"PASS: Python {mode} markers with 0..64 PCVs")


class ManyPCVs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "out").mkdir(exist_ok=True)
        cls.tmp = tempfile.TemporaryDirectory(prefix="pcv-regression-", dir=ROOT / "out")
        cls.directory = Path(cls.tmp.name)
        cls.c = cls.directory / "cpcvs"
        subprocess.run(["gcc", "-O2", "-Wall", "-Wextra", "-Werror", str(ROOT / "tests/cpcvs.c"),
                        "-o", str(cls.c), "-L"+str(ROOT / "build"), "-lperfmark",
                        "-Wl,-rpath,"+str(ROOT / "build")], check=True)
        cls.rust = cls.directory / "rpcvs"
        if shutil.which("rustc"):
            subprocess.run(["rustc", "--edition=2021", "-O", str(ROOT / "tests/rpcvs.rs"),
                            "-o", str(cls.rust), "-L", str(ROOT / "build"),
                            "-C", "link-arg=-Wl,-rpath,"+str(ROOT / "build")], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check_markers(self, label, command):
        raw = self.directory / label
        rc, log, files = runner.run(command, str(raw), timeout=60)
        self.assertEqual(rc, 0, log)
        self.assertTrue(files, log)
        runs = runner.load_runs(str(raw))
        self.assertEqual(runner.validity(runs), [])
        keys, _ = runner.blocks_of_set(runs)
        recs = runner.load_traces_all(runs)
        self.assertFalse(any(r["region"].startswith("invalid_") for r in recs))
        for n in COUNTS:
            region = f"pcvs_{n}"
            vecs, calls, names, nested, dropped = derive.inclusive_vectors(keys, region, recs)
            self.assertEqual(tuple(names), tuple(f"pcv_{j}" for j in range(n)))
            expected = {tuple(BASE+j+(variant if j == n-1 else 0) for j in range(n)) for variant in range(3)}
            self.assertEqual(set(vecs), expected, (label, region))
            self.assertEqual(sum(calls.values()), 6)
            self.assertTrue(all(count == (6 if n == 0 else 2) for count in calls.values()))
            self.assertEqual((nested, dropped), (0, 0))
            records = [r for r in recs if r["region"] == region]
            self.assertEqual(len(records), 6)
            self.assertTrue(all(r["nk"] == n for r in records))
            self.assertEqual({derive.key_state(r) for r in records}, expected)
            if label.startswith("python"):
                self.assertTrue(all(r["state"]["note"] == "extra" for r in records))

    def test_c(self):
        self.check_markers("c", [str(self.c)])

    def test_rust(self):
        if not self.rust.exists():
            self.skipTest("rustc unavailable")
        self.check_markers("rust", [str(self.rust)])

    def test_python_fast(self):
        self.check_markers("python_fast", [sys.executable, str(Path(__file__).resolve()), "--worker", "fast"])

    def test_python_ctypes(self):
        self.check_markers("python_ctypes", [sys.executable, str(Path(__file__).resolve()), "--worker", "ctypes"])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        python_worker(sys.argv[2])
    else:
        unittest.main()
