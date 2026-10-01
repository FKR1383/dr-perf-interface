import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import core
import vllm_suite


class VllmSuiteTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        staged = root / "staged"
        runtime = root / "runtime"
        staged.mkdir()
        runtime.mkdir()
        core.write_json(
            staged / "case.json", {"source": {"path": "vllm/target.py"}}
        )
        return staged, runtime

    def test_native_validation_rejects_fewer_than_eight_marker_hits(self):
        with tempfile.TemporaryDirectory() as temporary:
            staged, runtime = self._fixture(Path(temporary))
            completed = subprocess.CompletedProcess(
                [], 0, stdout=json.dumps({"marker_hits": {"vllm-001": 7}}), stderr=""
            )
            with patch.object(vllm_suite, "_link_runtime"), patch.object(
                vllm_suite.subprocess, "run", return_value=completed
            ):
                with self.assertRaisesRegex(
                    vllm_suite.VllmSuiteError, "required_marker_hits=8"
                ):
                    vllm_suite._native_validate(
                        "vllm-001", staged, runtime, "python"
                    )

    def test_native_validation_accepts_eight_marker_hits(self):
        with tempfile.TemporaryDirectory() as temporary:
            staged, runtime = self._fixture(Path(temporary))
            completed = subprocess.CompletedProcess(
                [], 0, stdout=json.dumps({"marker_hits": {"vllm-001": 8}}), stderr=""
            )
            with patch.object(vllm_suite, "_link_runtime"), patch.object(
                vllm_suite.subprocess, "run", return_value=completed
            ):
                result = vllm_suite._native_validate(
                    "vllm-001", staged, runtime, "python"
                )
            self.assertEqual(result["marker_hits"], 8)


if __name__ == "__main__":
    unittest.main()
