"""The workload contract applies to arbitrary workspaces, not a benchmark ID."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from evaluation import drperf_measure
from evaluation.measurement_session import MeasurementSession
from evaluation.results import EvaluationError, read_json, write_json
from evaluation.workload import FrozenWorkload, MANIFEST, WorkloadChanged


class WorkloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "original"
        self.original.mkdir()
        (self.original / "kernel.py").write_text(
            "import perfmark\nsize = 5\nwith perfmark.region('work'):\n    result = size * 2\n")
        (self.original / "driver.py").write_text("sizes = [1, 2, 4, 8]\n")
        (self.original / "inputs.json").write_text("[1, 2, 4, 8]")
        self.definition = {"version": 1, "instrumentation": {"kernel.py": {"kind": "python-marker"}}}
        write_json(self.original / MANIFEST, self.definition)
        self.frozen = FrozenWorkload(self.original, "work")
        self.edited = self.root / "edited"
        shutil.copytree(self.original, self.edited)

    def test_all_files_and_assignments_are_fixed_except_marker_keywords(self):
        kernel = self.edited / "kernel.py"
        kernel.write_text(kernel.read_text().replace("region('work')", "region('work', **{'size': size})"))
        self.frozen.validate(self.edited)
        changes = {"driver.py": "sizes = [3, 9]\n", "inputs.json": "[3, 9]", MANIFEST: "{}",
                   "kernel.py": kernel.read_text().replace("size = 5", "size = 7"),
                   "extra.py": "# unexpected helper"}
        for name, value in changes.items():
            with self.subTest(name=name):
                path = self.edited / name
                previous = path.read_bytes() if path.exists() else None
                path.write_text(value)
                with self.assertRaises(WorkloadChanged):
                    self.frozen.validate(self.edited)
                if previous is None:
                    path.unlink()
                else:
                    path.write_bytes(previous)

    def test_marker_boundary_and_region_body_cannot_change(self):
        original = (self.original / "kernel.py").read_text()
        for text in (original.replace("* 2", "* 3"), original.replace("'work'", "'other'"),
                     original.replace("    result", "result")):
            (self.edited / "kernel.py").write_text(text)
            with self.assertRaises(WorkloadChanged):
                self.frozen.validate(self.edited)

    def test_missing_files_and_new_symlinks_are_rejected(self):
        data = self.edited / "inputs.json"
        data.unlink()
        with self.assertRaises(WorkloadChanged):
            self.frozen.validate(self.edited)
        data.symlink_to(self.original / "inputs.json")
        with self.assertRaisesRegex(WorkloadChanged, "symlink"):
            self.frozen.validate(self.edited)

    def test_no_definition_and_unsafe_paths_fail_before_measurement(self):
        (self.original / MANIFEST).unlink()
        with self.assertRaisesRegex(EvaluationError, "missing workload definition"):
            FrozenWorkload(self.original, "work")
        for name in ("../outside", "/tmp/outside", "__pycache__/source.py", ""):
            write_json(self.original / MANIFEST, {**self.definition, "instrumentation": {name: {"kind": "python-marker"}}})
            with self.assertRaises(EvaluationError):
                FrozenWorkload(self.original, "work")

    def test_workload_changes_never_reach_worker_and_cannot_receive_a_score(self):
        session = MeasurementSession(self.root / "runtime", self.original, self.frozen, ["python3", "driver.py"])
        (self.edited / "inputs.json").write_text("[999]")
        journal = self.root / "journal"
        out = journal / "attempt-001"
        with patch.object(session, "_run_worker") as worker:
            value = session.measure(self.edited, ["python3", "driver.py"], out, "work", ["size"])
        worker.assert_not_called()
        self.assertEqual(value["status"], "invalid_measurement")
        self.assertIsNone(value["irregularity"])
        write_json(out / "request.json", {"variables": ["size"]})
        write_json(out / "measurement.json", {"attempt": 1, "variables": ["size"], **value})
        config = {"journal": str(journal), "max_attempts": 1, "region": "work"}
        self.assertEqual(drperf_measure.recorded_attempts(config)[0]["status"], "invalid_measurement")
        write_json(out / "measurement.json", {"attempt": 1, "variables": ["size"],
                                               "status": "ok", "formula": "1", "irregularity": 0})
        with self.assertRaisesRegex(EvaluationError, "rejected workload"):
            drperf_measure.recorded_attempts(config)

    def test_changed_command_is_rejected(self):
        session = MeasurementSession(self.root / "runtime", self.original, self.frozen, ["python3", "driver.py", "--seed", "7"])
        with patch.object(session, "_run_worker") as worker:
            value = session.measure(self.edited, ["python3", "driver.py", "--seed", "8"],
                                    self.root / "out", "work", ["size"])
        worker.assert_not_called()
        self.assertEqual(value["status"], "invalid_measurement")

    def test_common_feature_assignments_are_checked_in_call_order(self):
        session = MeasurementSession(self.root / "runtime", self.original, self.frozen)
        def traces(states):
            return [{"region": "work", "state": state} for state in states]
        sequences = [[{"n": 1}, {"n": 2}], [{"n": 1, "m": 4}, {"n": 2, "m": 9}],
                     [{"n": 2}, {"n": 1}], [{"m": 4}, {"m": 8}], [{"n": 1}]]
        with patch.object(drperf_measure.runner, "load_runs"), \
             patch.object(drperf_measure.runner, "load_traces_all", side_effect=[traces(s) for s in sequences]):
            for _ in range(2):
                self.assertEqual(session.validate_states(self.root, "work"), 2)
            for _ in range(3):
                with self.assertRaises(WorkloadChanged):
                    session.validate_states(self.root, "work")

    def test_actual_input_trace_checks_full_values_and_order(self):
        write_json(self.original / MANIFEST, {**self.definition, "input_trace": "assignments.json"})
        frozen = FrozenWorkload(self.original, "work")
        with self.assertRaisesRegex(WorkloadChanged, "did not produce"):
            frozen.validate_trace(self.edited)
        records = [{"n": 2, "array": [1, 3]}, {"n": 2, "array": [5, 7]}]
        write_json(self.edited / "assignments.json", records)
        first = frozen.validate_trace(self.edited)
        self.assertEqual(first, frozen.validate_trace(self.edited))
        for changed in (list(reversed(records)), [records[0]], [{"n": 2, "array": [1, 4]}, records[1]]):
            write_json(self.edited / "assignments.json", changed)
            with self.assertRaisesRegex(WorkloadChanged, "actual workload inputs"):
                frozen.validate_trace(self.edited)

    def test_fixed_native_build_and_bounded_source_edits(self):
        # A real worker rebuilds a tiny executable from a protected build command.
        # No compiler, Dr. Perf, or LLM is needed: this test exits at the build
        # validation check after the build deliberately changes protected data.
        (self.original / "driver.c").write_text("int n = 4;\n/* BEGIN */\nmarker(n);\n/* END */\nwork(n);\n")
        (self.original / "build.py").write_text(
            "from pathlib import Path\n"
            "assert not Path('program').exists()\n"
            "Path('program').write_text('rebuilt')\n"
            "Path('inputs.json').write_text('[123]')\n")
        definition = {"version": 1, "instrumentation": {"driver.c": {
            "kind": "text-block", "start": "/* BEGIN */", "end": "/* END */"}},
            "build": [sys.executable, "build.py"], "build_outputs": ["program"]}
        write_json(self.original / MANIFEST, definition)
        frozen = FrozenWorkload(self.original, "work")
        (self.original / "program").write_text("agent-built executable must not run")
        session = MeasurementSession(self.root / "runtime", self.original, frozen, ["./program"])
        out = self.root / "out"
        value = session.measure(self.original, ["./program"], out, "work", ["n"])
        self.assertEqual(value["status"], "invalid_measurement", value)
        self.assertIn("inputs.json", value["details"]["message"])
        self.assertTrue((out / "build.log").exists())
        self.assertFalse((out / "process.json").exists())
        self.assertEqual((self.original / "inputs.json").read_text(), "[1, 2, 4, 8]")
        source = self.original / "driver.c"
        source.write_text(source.read_text().replace("marker(n);", "marker(n, n*n);"))
        frozen.validate(self.original)
        source.write_text(source.read_text().replace("n = 4", "n = 9"))
        with self.assertRaises(WorkloadChanged):
            frozen.validate(self.original)
