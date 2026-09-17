"""Frozen-answer measurement tests; Codex is substituted, never called live."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from evaluation import baseline_measure as baseline, codex_runner, drperf_measure
from evaluation.results import EvaluationError, validate_result


def ready(names):
    return {"status": "ready", "reason": "", "bindings": [
        {"variable": n, "expression": n, "location": "driver.c:1"} for n in names]}


class BaselineMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "driver.c").write_text("original source\n")
        self.out = self.root / "measurement"
        self.control = self.root / "control"

    def measure(self, names):
        return baseline.measure("codex", self.workspace, self.control, self.out,
                                "parse", ["./program", "cases=5"], names, "chosen-model")

    def test_exact_set_measured_once_after_instrumenter_exits(self):
        names = ["n", "n^2"]
        events = []

        def instrument(executable, competitor, workspace, control, prompt, **kwargs):
            events.append("instrument")
            self.assertEqual(competitor, "agent_only_instrumentation")
            self.assertEqual(kwargs["model"], "chosen-model")
            self.assertIn(json.dumps(names), prompt)
            (workspace / "driver.c").write_text("frozen bindings: n and n*n\n")
            events.append("instrumenter_finished")
            value = ready(names)
            value["bindings"][1]["expression"] = "(int64_t)n*n"
            return value

        def measure(command, out, region, expected):
            self.assertEqual(events[-1], "instrumenter_finished")
            self.assertEqual(Path.cwd(), self.workspace)
            self.assertEqual(expected, names)
            self.assertEqual(command, ["./program", "cases=5"])
            events.append("measure")
            return {"formula": "3*n^2 + 9", "irregularity": 0.42, "status": "ok", "details": {}}

        original_cwd = Path.cwd()
        with patch.object(codex_runner, "invoke", side_effect=instrument) as instrumented, \
             patch.object(drperf_measure, "measure", side_effect=measure) as measured:
            value = self.measure(names)
        self.assertEqual(instrumented.call_count, 1)
        self.assertEqual(measured.call_count, 1)  # No feedback retry even at 42%.
        self.assertEqual(events, ["instrument", "instrumenter_finished", "measure"])
        self.assertEqual(Path.cwd(), original_cwd)
        self.assertEqual(value["variables"], names)
        self.assertEqual(value["irregularity"], 0.42)
        self.assertEqual(json.loads((self.out / "measurement.json").read_text()), value)
        self.assertIn("frozen bindings", (self.out / "instrumentation.patch").read_text())

    def test_known_native_limits_do_not_launch_instrumenter_or_drop_features(self):
        cases = [([], "insufficient_state_variation"),
                 (["a", "b", "c", "d", "e"], "unsupported_state_count"),
                 (["x" * 64], "unsupported_state_name"),
                 (["é" * 32], "unsupported_state_name"),
                 (["x\0y"], "unsupported_state_name")]
        for names, status in cases:
            with self.subTest(status=status, names=names), \
                 patch.object(codex_runner, "invoke") as instrumented, \
                 patch.object(drperf_measure, "measure") as measured:
                value = self.measure(names)
                self.assertEqual(value["variables"], names)
                self.assertEqual(value["status"], status)
                self.assertIsNone(value["irregularity"])
                instrumented.assert_not_called()
                measured.assert_not_called()
        # The discovery contract still accepts more than four features.
        self.assertEqual(len(validate_result({"variables": ["a", "b", "c", "d", "e"]},
                                            "agent_only")["variables"]), 5)

    def test_unsupported_pointer_and_binding_changes_are_not_measured(self):
        answers = [({"status": "unsupported", "reason": "input is a buffer pointer", "bindings": []},
                    "unsupported_features"),
                   (ready(["length"]), "instrumentation_error"),
                   (ready([]), "instrumentation_error"),
                   (ready(["input", "input"]), "instrumentation_error")]
        for answer, status in answers:
            with self.subTest(answer=answer), \
                 patch.object(codex_runner, "invoke", return_value=answer), \
                 patch.object(drperf_measure, "measure") as measured:
                value = self.measure(["input"])
                self.assertEqual(value["status"], status)
                self.assertEqual(value["variables"], ["input"])
                self.assertIsNone(value["formula"])
                measured.assert_not_called()

    def test_instrumenter_failure_and_invalid_native_result_stay_unavailable(self):
        with patch.object(codex_runner, "invoke", side_effect=EvaluationError("build failed")):
            value = self.measure(["n"])
        self.assertEqual(value["status"], "instrumentation_error")
        self.assertIsNone(value["irregularity"])
        self.assertIn("build failed", value["details"]["message"])
        failed = drperf_measure.failed("state_mismatch", "actual labels differ")
        with patch.object(codex_runner, "invoke", return_value=ready(["n"])), \
             patch.object(drperf_measure, "measure", return_value=failed) as measured:
            value = self.measure(["n"])
        measured.assert_called_once()
        self.assertEqual(value["status"], "state_mismatch")
        self.assertIsNone(value["irregularity"])

    def test_instrumentation_result_schema(self):
        def fake_codex(command, **kwargs):
            self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
            self.assertNotIn("--add-dir", command)
            output = Path(command[command.index("--output-last-message") + 1])
            output.write_text(json.dumps(ready(["n"])))
            return subprocess.CompletedProcess(command, 0)

        with patch.object(codex_runner.subprocess, "run", side_effect=fake_codex):
            answer = codex_runner.invoke("codex", "agent_only_instrumentation", self.workspace,
                                          self.control, "instrument only")
        self.assertEqual(answer, ready(["n"]))


@unittest.skipUnless(os.environ.get("DRPERF_EVAL_INTEGRATION") == "1",
                     "set DRPERF_EVAL_INTEGRATION=1 for native frozen-answer measurements")
class NativeBaselineTests(unittest.TestCase):
    def test_frozen_derived_expression_uses_real_drperf(self):
        drperf_measure.check_build()
        root = drperf_measure.ROOT
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "workspace"
            (workspace / "perfmark").mkdir(parents=True)
            shutil.copyfile(root / "perfmark/perfmark.h", workspace / "perfmark/perfmark.h")
            source = workspace / "driver.c"
            source.write_text('''#include "perfmark/perfmark.h"
volatile unsigned long sum;
int main(void) {
    for (int n = 10; n <= 100; n += 10) {
        perfmark_begin("work", "n", n);
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j) sum += i + j;
        perfmark_end("work");
    }
    return 0;
}
''')

            def instrument(*args, **kwargs):
                source.write_text(source.read_text().replace('"n", n', '"n^2", (int64_t)n*n'))
                subprocess.run(["cc", "-O2", "-g", "driver.c", "-L" + str(root / "build"),
                                "-lperfmark", "-Wl,-rpath," + str(root / "build"), "-o", "program"],
                               cwd=workspace, check=True)
                return {"status": "ready", "reason": "", "bindings": [
                    {"variable": "n^2", "expression": "(int64_t)n*n", "location": "driver.c:5"}]}

            with patch.object(codex_runner, "invoke", side_effect=instrument) as instrumented:
                value = baseline.measure("codex", workspace, base / "control", base / "measurement",
                                         "work", ["./program"], ["n^2"])
            instrumented.assert_called_once()
            self.assertEqual(value["status"], "ok", value)
            self.assertIn("n^2", value["formula"])
            self.assertIsInstance(value["irregularity"], float)
            self.assertEqual(value["details"]["calls"], 10)
            self.assertTrue((base / "measurement/raw").is_dir())


if __name__ == "__main__":
    unittest.main()
