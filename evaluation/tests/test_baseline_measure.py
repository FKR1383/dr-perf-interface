"""Frozen-answer measurement tests; Codex is substituted, never called live."""
import json
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from evaluation import baseline_measure as baseline, codex_runner, drperf_measure, run
from evaluation.results import EvaluationError, validate_result


def ready(names):
    return {"status": "ready", "reason": "", "advice": "", "bindings": [
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

    def test_many_features_are_bound_and_measured_in_full(self):
        names = [f"s{i}" for i in range(9)]
        failure = drperf_measure.failed("insufficient_state_variation", "needs 11 distinct states")
        with patch.object(codex_runner, "invoke", return_value=ready(names)) as instrumented, \
             patch.object(drperf_measure, "measure", return_value=failure) as measured:
            value = self.measure(names)
        instrumented.assert_called_once()
        self.assertIn(json.dumps(names), instrumented.call_args.args[4])
        self.assertEqual(measured.call_args.args[-1], names)
        self.assertEqual(value["variables"], names)
        self.assertEqual(value["status"], "insufficient_state_variation")
        self.assertTrue(baseline.retryable(value))

    def test_unsupported_pointer_and_binding_changes_are_not_measured(self):
        answers = [({"status": "unsupported", "reason": "input is a buffer pointer", "advice": "Define a scalar.", "bindings": []},
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


class MeasurabilityLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "driver.c").write_text("untouched source\n")
        self.captured = {}

    def loop(self, rounds=3):
        with contextlib.redirect_stderr(io.StringIO()):
            return run.agent_only_search("codex", self.source, self.source, "work",
                                         [str(self.source / "program"), "fixed=1"],
                                         self.captured, "model-name", rounds)

    def test_array_revised_with_advice_then_stop_even_at_high_irregularity(self):
        events, static_prompts, old_sessions = [], [], []
        candidate = ["feature[i][j] for all i,j", "n"]
        advice = "An array is not a scalar state; define the exact scalar expression you intend."

        def invoke(executable, competitor, workspace, control, prompt, **kwargs):
            for old in old_sessions:
                self.assertFalse(old.exists())
            old_sessions.append(workspace.parent)
            self.assertEqual((workspace / "driver.c").read_text(), "untouched source\n")
            self.assertFalse((workspace / "private-evidence.log").exists())
            self.assertEqual(kwargs["model"], "model-name")
            control.mkdir()
            (control / "codex.log").write_text("private-evidence-log")
            (control / "codex-home").mkdir()
            (control / "codex-home/auth.json").write_text("do not export")
            events.append(competitor)
            if competitor == "agent_only":
                static_prompts.append(prompt)
                self.assertNotIn("private-evidence", prompt)
                if len(static_prompts) == 1:
                    return {"variables": candidate}
                self.assertIn(advice, prompt)
                return {"variables": ["n"]}
            (workspace / "driver.c").write_text("instrumentation changes\n")
            (workspace / "private-evidence.log").write_text("not for static sessions")
            if len(static_prompts) == 1:
                return {"status": "unsupported", "reason": "feature is a floating-point matrix",
                        "advice": advice, "bindings": []}
            return ready(["n"])

        def measure(command, out, region, expected):
            events.append("native_measurement")
            self.assertEqual(command, [str(Path.cwd() / "program"), "fixed=1"])
            self.assertEqual(expected, ["n"])
            return {"formula": "private-performance-formula", "irregularity": 0.9999,
                    "status": "ok", "details": {"unexplained_functions": ["private-cost-details"]}}

        with patch.object(codex_runner, "invoke", side_effect=invoke), \
             patch.object(drperf_measure, "measure", side_effect=measure) as measured:
            result = self.loop()
        self.assertEqual(events, ["agent_only", "agent_only_instrumentation", "agent_only",
                                  "agent_only_instrumentation", "native_measurement"])
        measured.assert_called_once()
        self.assertEqual(result["agent_only_initial"]["variables"], candidate)
        self.assertEqual(result["agent_only"]["variables"], ["n"])
        metadata = result["agent_only_measurability"]
        self.assertEqual(metadata["rounds_used"], 2)
        self.assertEqual(metadata["stop_reason"], "measurable")
        self.assertNotIn("private-performance", json.dumps(metadata))
        self.assertNotIn("private-cost", json.dumps(metadata))
        self.assertNotIn("0.9999", json.dumps(metadata))
        self.assertEqual(result["agent_only_measurement"]["irregularity"], 0.9999)
        self.assertEqual((self.source / "driver.c").read_text(), "untouched source\n")
        self.assertIn("measurements/agent_only/round-001/instrumentation.json", self.captured)
        self.assertIn("measurements/agent_only/round-002/measurement.json", self.captured)
        self.assertFalse(any("auth.json" in name for name in self.captured))
        self.assertTrue(all(not p.exists() for p in old_sessions))

    def test_native_diagnostics_are_not_forwarded_to_static_revision(self):
        prompts = []

        def invoke(executable, competitor, workspace, control, prompt, **kwargs):
            if competitor == "agent_only":
                prompts.append(prompt)
                self.assertNotIn("LEAK_NATIVE_RESULT", prompt)
                self.assertNotIn("0.812345", prompt)
                return {"variables": ["n"] if len(prompts) == 1 else ["m"]}
            return ready(["n"] if len(prompts) == 1 else ["m"])

        failure = drperf_measure.failed("insufficient_state_variation", "LEAK_NATIVE_RESULT",
                                       instruction_count=812345, irregularity=0.812345,
                                       formula="LEAK_NATIVE_RESULT")
        success = {"status": "ok", "formula": "7*m", "irregularity": 1.0, "details": {}}
        with patch.object(codex_runner, "invoke", side_effect=invoke), \
             patch.object(drperf_measure, "measure", side_effect=[failure, success]) as measured:
            result = self.loop()
        self.assertEqual(measured.call_count, 2)
        self.assertEqual(len(prompts), 2)
        self.assertIn("enough distinct state combinations", prompts[1])
        self.assertEqual(result["agent_only_measurability"]["stop_reason"], "measurable")

    def test_round_budget_preserves_all_failed_proposals(self):
        def invoke(executable, competitor, *args, **kwargs):
            if competitor == "agent_only":
                return {"variables": ["array"]}
            return {"status": "unsupported", "reason": "array-valued", "advice": "Define a scalar.",
                    "bindings": []}

        with patch.object(codex_runner, "invoke", side_effect=invoke) as invoked, \
             patch.object(drperf_measure, "measure") as measured:
            result = self.loop(rounds=2)
        self.assertEqual(invoked.call_count, 4)
        measured.assert_not_called()
        metadata = result["agent_only_measurability"]
        self.assertEqual(metadata["rounds_used"], 2)
        self.assertEqual(metadata["stop_reason"], "round_limit_reached")
        self.assertFalse(metadata["measurable"])
        self.assertIsNone(result["agent_only_measurement"]["irregularity"])

    def test_tool_failure_does_not_request_cost_feature_revision(self):
        def invoke(executable, competitor, *args, **kwargs):
            return {"variables": ["n"]} if competitor == "agent_only" else ready(["n"])

        with patch.object(codex_runner, "invoke", side_effect=invoke) as invoked, \
             patch.object(drperf_measure, "measure", return_value=drperf_measure.failed(
                 "workload_failed", "LEAK_EXECUTION_OUTPUT")):
            result = self.loop()
        self.assertEqual(invoked.call_count, 2)
        self.assertEqual(result["agent_only_measurability"]["stop_reason"], "measurement_unavailable")
        self.assertNotIn("LEAK_EXECUTION_OUTPUT", json.dumps(result["agent_only_measurability"]))


@unittest.skipUnless(os.environ.get("DRPERF_EVAL_INTEGRATION") == "1",
                     "set DRPERF_EVAL_INTEGRATION=1 for native frozen-answer measurements")
class NativeBaselineTests(unittest.TestCase):
    def test_nine_features_through_both_adapters_and_result_validation(self):
        drperf_measure.check_build()
        root = drperf_measure.ROOT
        names = [f"s{i}" for i in range(9)]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "workspace"
            workspace.mkdir()
            source = workspace / "driver.c"
            source.write_text('''#include "perfmark.h"
volatile unsigned long total;
int main(void) {
    const char *names[] = {"s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"};
    for (int point = 0; point < 19; ++point) {
        int64_t values[9];
        for (int j = 0; j < 9; ++j)
            values[j] = 10 + (point > 0 && (point-1)/2 == j ? (point%2 ? 7 : 31) : 0);
        /* STATES */
        for (int j = 0; j < 9; ++j)
            for (int64_t i = 0; i < values[j]; ++i) total += i;
        perfmark_end("work");
    }
    return 0;
}
''')

            def instrument(*args, **kwargs):
                source.write_text(source.read_text().replace(
                    '/* STATES */', 'perfmark_begin_v("work", 9, names, values);'))
                subprocess.run(["cc", "-O2", "-I" + str(root / "perfmark"), "driver.c",
                                "-L" + str(root / "build"), "-lperfmark",
                                "-Wl,-rpath," + str(root / "build"), "-o", "program"],
                               cwd=workspace, check=True)
                return ready(names)

            with patch.object(codex_runner, "invoke", side_effect=instrument) as instrumented:
                baseline_value = baseline.measure("codex", workspace, base / "control",
                                                  base / "baseline", "work", ["./program"], names)
            instrumented.assert_called_once()
            self.assertEqual(baseline_value["status"], "ok", baseline_value)
            self.assertEqual(baseline_value["variables"], names)
            config = {"workspace": str(workspace), "journal": str(base / "journal"),
                      "region": "work", "command": ["./program"], "max_attempts": 1}
            previous = Path.cwd()
            try:
                os.chdir(workspace)
                experimental = drperf_measure.attempt(config, names)
            finally:
                os.chdir(previous)
            self.assertEqual(experimental["status"], "ok", experimental)
            self.assertEqual(experimental["formula"], baseline_value["formula"])
            self.assertEqual(experimental["irregularity"], baseline_value["irregularity"])
            self.assertEqual(experimental["details"]["calls"], 19)
            self.assertEqual(experimental["details"]["regimes"][0]["dependent_states"], [])
            records = drperf_measure.recorded_attempts(config)
            answer = {"attempts": records, "selected_variables": names,
                      "final_formula": experimental["formula"],
                      "final_irregularity": experimental["irregularity"]}
            self.assertEqual(validate_result(answer, "agent_drperf")["selected_variables"], names)

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
                return {"status": "ready", "reason": "", "advice": "", "bindings": [
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
