import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import core
import wan_suite


class WanSuiteTests(unittest.TestCase):
    def test_runtime_revision_rejects_sparse_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(wan_suite.WanSuiteError, "complete Diffusers"):
                wan_suite._runtime_revision(Path(temporary))

    def test_copy_runtime_overlays_submitted_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / "template"
            staged = root / "staged"
            (template / "src/diffusers").mkdir(parents=True)
            (staged / "src/diffusers").mkdir(parents=True)
            (template / "src/diffusers/target.py").write_text("old\n")
            (staged / "src/diffusers/target.py").write_text("candidate\n")
            wan_suite._copy_runtime(template, root / "runtime", staged, "src/diffusers/target.py")
            self.assertEqual((root / "runtime/src/diffusers/target.py").read_text(), "candidate\n")

    def test_native_validation_requires_six_marker_hits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged = root / "staged"
            runtime = root / "template"
            (staged / "tests").mkdir(parents=True)
            (staged / "src/diffusers").mkdir(parents=True)
            (runtime / "src/diffusers").mkdir(parents=True)
            (staged / "src/diffusers/target.py").write_text("candidate\n")
            (runtime / "src/diffusers/target.py").write_text("old\n")
            (staged / "tests/test_case.py").write_text("pass\n")
            core.write_json(staged / "case.json", {"source": {"path": "src/diffusers/target.py"}})
            completed = subprocess.CompletedProcess(
                [], 0, stdout=json.dumps({"marker_hits": {"wan-001": 5}}), stderr=""
            )
            with patch.object(wan_suite.subprocess, "run", return_value=completed):
                with self.assertRaisesRegex(wan_suite.WanSuiteError, "native workload validation failed"):
                    wan_suite._native_validate("wan-001", staged, runtime, "python")


if __name__ == "__main__":
    unittest.main()
