import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import core


def valid_metrics(share=0.099):
    return {
        "returncode": 0,
        "raw_files": ["run.1.json"],
        "validity_warnings": [],
        "pcv_names": ["n"],
        "distinct_states": 3,
        "required_states": 3,
        "calls": 3,
        "dropped_calls": 0,
        "nested_calls_per_call": 0.0,
        "states": [{"state": {"n": 1}, "unexplained_share": share}],
        "sufficient_points": True,
        "max_unexplained_share": share,
        "formula": {"coefficients": {"n": 1000}, "constant": 20},
    }


class ScoringTests(unittest.TestCase):
    def test_below_threshold_succeeds(self):
        result = core.assess_metrics(valid_metrics(0.099999), 10.0)
        self.assertTrue(result["success"])

    def test_nonfinite_irregularity_is_invalid(self):
        result = core.assess_metrics(valid_metrics(float("nan")), 10.0)
        self.assertFalse(result["valid"])
        self.assertFalse(result["success"])

    def test_threshold_is_strict(self):
        result = core.assess_metrics(valid_metrics(0.10), 10.0)
        self.assertTrue(result["valid"])
        self.assertFalse(result["success"])

    def test_invalid_measurement_never_succeeds(self):
        metrics = valid_metrics(0.01)
        metrics["validity_warnings"] = ["counter overflow"]
        result = core.assess_metrics(metrics, 10.0)
        self.assertFalse(result["valid"])
        self.assertFalse(result["success"])

    def test_measured_pcvs_must_match_submission(self):
        result = core.assess_metrics(valid_metrics(0.01), 10.0, ["different_name"])
        self.assertFalse(result["valid"])
        self.assertFalse(result["success"])
        self.assertIn("do not match", result["reasons"][-1])

    def test_invalid_scored_feedback_still_returns_only_percentage(self):
        metrics = valid_metrics(0.20)
        metrics["validity_warnings"] = ["counter overflow"]
        assessment = core.assess_metrics(metrics, 10.0)
        feedback = core.redacted_feedback(1, assessment, "invalid")
        self.assertNotIn("reasons", feedback)
        self.assertEqual(feedback["irregularity_percent"], 20.0)

    def test_feedback_does_not_leak_formula_or_attribution(self):
        assessment = core.assess_metrics(valid_metrics(), 10.0)
        feedback = core.redacted_feedback(1, assessment, "success")
        self.assertEqual(
            set(feedback),
            {"iteration", "status", "irregularity_percent", "threshold_percent", "comparison"},
        )
        self.assertNotIn("formula", json.dumps(feedback))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run = Path(self.temp.name) / "run"
        core.start("aq-001", self.run)

    def tearDown(self):
        self.temp.cleanup()

    def annotate(self, iteration=1):
        state = core.load_state(self.run)
        source = self.run / "selector" / "workspace" / state["source_path"]
        text = source.read_text()
        old = "perfmark.region('aq-001')"
        if old not in text:
            old = 'perfmark.region("aq-001")'
        self.assertIn(old, text)
        source.write_text(text.replace(old, old[:-1] + ", n=len(enum_class._member_map_))", 1))
        core.write_json(
            self.run / "selector" / "workspace" / core.CANDIDATE_FILE,
            {
                "iteration": iteration,
                "pcvs": [{
                    "name": "n",
                    "expression": "len(enum_class._member_map_)",
                    "rationale": "The marked search visits prior members.",
                }],
                "hypothesis": "instructions = a*n + constant",
            },
        )

    def test_start_uses_empty_marker_and_hides_prior_result(self):
        workspace = self.run / "selector" / "workspace"
        state = core.load_state(self.run)
        source = (workspace / state["source_path"]).read_text()
        self.assertIn("perfmark.region('aq-001')", source)
        self.assertFalse((workspace / "result.json").exists())
        self.assertFalse((workspace / "reference.md").exists())

    def test_protected_test_change_is_rejected(self):
        self.annotate()
        test = self.run / "selector" / "workspace" / "tests" / "test_case.py"
        test.write_text(test.read_text() + "\n# changed\n")
        with self.assertRaisesRegex(core.EvaluationError, "protected benchmark file"):
            core.submit(self.run)

    def test_success_records_first_iteration(self):
        self.annotate()
        core.submit(self.run)

        def fake_run(command, **kwargs):
            out = Path(command[command.index("--out") + 1])
            out.mkdir(parents=True)
            core.write_json(out / "metrics.json", valid_metrics(0.075))
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch.object(core.subprocess, "run", side_effect=fake_run):
            feedback, _ = core.measure(self.run)
        self.assertEqual(feedback["status"], "success")
        self.assertAlmostEqual(feedback["irregularity_percent"], 7.5)
        summary = core.read_json(self.run / "summary.json")
        self.assertEqual(summary["iterations_evaluated"], 1)
        self.assertEqual(summary["success_iteration"], 1)

    def test_failed_score_advances_iteration_with_redacted_feedback(self):
        self.annotate()
        core.submit(self.run)

        def fake_run(command, **kwargs):
            out = Path(command[command.index("--out") + 1])
            out.mkdir(parents=True)
            core.write_json(out / "metrics.json", valid_metrics(0.25))
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch.object(core.subprocess, "run", side_effect=fake_run):
            feedback, _ = core.measure(self.run)
        self.assertEqual(feedback["status"], "retry")
        self.assertEqual(feedback["irregularity_percent"], 25.0)
        self.assertNotIn("formula", json.dumps(feedback))
        state = core.load_state(self.run)
        self.assertEqual(state["next_iteration"], 2)
        candidate = core.read_json(self.run / "selector" / "workspace" / core.CANDIDATE_FILE)
        self.assertEqual(candidate["iteration"], 2)

    def test_measurement_error_does_not_consume_iteration(self):
        self.annotate()
        core.submit(self.run)
        failed = subprocess.CompletedProcess([], 1, stdout="", stderr="failed")
        with patch.object(core.subprocess, "run", return_value=failed):
            feedback, _ = core.measure(self.run)
        self.assertEqual(feedback["status"], "measurement-error")
        state = core.load_state(self.run)
        self.assertEqual(state["status"], "awaiting-measurement")
        summary = core.read_json(self.run / "summary.json")
        self.assertEqual(summary["iterations_evaluated"], 0)

    def test_interrupted_unrecorded_measurement_uses_next_free_directory(self):
        self.annotate()
        core.submit(self.run)
        attempt = core.load_state(self.run)["attempts"][-1]
        orphan = self.run / attempt["path"] / "measurement" / "run-001"
        orphan.mkdir(parents=True)
        (orphan / "partial.trace").write_text("interrupted")

        def fake_run(command, **kwargs):
            out = Path(command[command.index("--out") + 1])
            self.assertEqual(out.name, "run-002")
            out.mkdir(parents=True)
            core.write_json(out / "metrics.json", valid_metrics(0.075))
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch.object(core.subprocess, "run", side_effect=fake_run):
            feedback, _ = core.measure(self.run)
        self.assertEqual(feedback["status"], "success")
        self.assertTrue((orphan / "partial.trace").is_file())
        state = core.load_state(self.run)
        self.assertEqual(
            state["attempts"][-1]["measurement_runs"][-1]["path"],
            "measurement/run-002",
        )

    def test_workload_failure_with_raw_measurement_consumes_invalid_iteration(self):
        self.annotate()
        core.submit(self.run)

        def fake_run(command, **kwargs):
            out = Path(command[command.index("--out") + 1])
            out.mkdir(parents=True)
            metrics = valid_metrics()
            metrics.update({
                "returncode": 1,
                "distinct_states": 1,
                "sufficient_points": False,
                "max_unexplained_share": None,
            })
            core.write_json(out / "metrics.json", metrics)
            return subprocess.CompletedProcess(command, 1, stdout="failed", stderr="")

        with patch.object(core.subprocess, "run", side_effect=fake_run):
            feedback, assessment = core.measure(self.run)
        self.assertEqual(feedback["status"], "invalid")
        self.assertFalse(assessment["valid"])
        state = core.load_state(self.run)
        self.assertEqual(state["status"], "awaiting-selector")
        self.assertEqual(state["next_iteration"], 2)
        self.assertEqual(state["attempts"][-1]["outcome"], "invalid")


if __name__ == "__main__":
    unittest.main()
