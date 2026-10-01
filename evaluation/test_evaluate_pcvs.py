from pathlib import Path
import unittest
from unittest.mock import patch

import evaluate_pcvs


CANDIDATE = {
    "iteration": 1,
    "pcvs": [{
        "name": "items",
        "expression": "len(requests)",
        "rationale": "counts the processed requests",
    }],
    "hypothesis": "work grows with request count",
}


class SubmitCandidateTests(unittest.TestCase):
    @patch("evaluate_pcvs.core.submit")
    @patch("evaluate_pcvs.strict_wan._apply_candidate")
    @patch("evaluate_pcvs.core.load_state")
    def test_submit_uses_current_iteration_and_snapshots(self, load, apply, submit):
        load.return_value = {"status": "awaiting-selector", "next_iteration": 1}
        apply.return_value = CANDIDATE
        result = evaluate_pcvs.submit_candidate(Path("/tmp/example"), CANDIDATE)
        apply.assert_called_once_with(Path("/tmp/example"), CANDIDATE, 1)
        submit.assert_called_once_with(Path("/tmp/example"))
        self.assertEqual(result, CANDIDATE)

    @patch("evaluate_pcvs.core.load_state")
    def test_submit_rejects_wrong_lifecycle_state(self, load):
        load.return_value = {"status": "success"}
        with self.assertRaisesRegex(evaluate_pcvs.PcvEvaluatorError, "cannot accept"):
            evaluate_pcvs.submit_candidate(Path("/tmp/example"), CANDIDATE)


class MeasureCandidateTests(unittest.TestCase):
    @patch("evaluate_pcvs._measurement_payload")
    @patch("evaluate_pcvs.vllm_suite.measure_case")
    @patch("evaluate_pcvs.core.load_state")
    def test_vllm_measurement_returns_complete_payload(self, load, measure, payload):
        load.return_value = {
            "status": "awaiting-measurement",
            "case_id": "vllm-005",
        }
        measure.return_value = (
            {"status": "retry", "irregularity_percent": 12.0},
            {"valid": True, "success": False},
        )
        payload.return_value = {"drperf_full_report": {"states": [1]}}
        result = evaluate_pcvs.measure_candidate(
            "vllm", Path("/tmp/root/vllm-005"), timeout=321.0
        )
        measure.assert_called_once_with(
            Path("/tmp/root"), "vllm-005", timeout=321.0
        )
        self.assertEqual(result["drperf_full_report"], {"states": [1]})

    @patch("evaluate_pcvs.core.load_state")
    def test_measure_rejects_unsubmitted_case(self, load):
        load.return_value = {"status": "awaiting-selector"}
        with self.assertRaisesRegex(evaluate_pcvs.PcvEvaluatorError, "cannot measure"):
            evaluate_pcvs.measure_candidate("vllm", Path("/tmp/root/vllm-005"))


class EvaluateCandidateTests(unittest.TestCase):
    @patch("evaluate_pcvs.measure_candidate")
    @patch("evaluate_pcvs.submit_candidate")
    @patch("evaluate_pcvs.core.load_state")
    def test_json_in_to_full_report_out(self, load, submit, measure):
        load.return_value = {"status": "awaiting-selector"}
        submit.return_value = CANDIDATE
        measure.return_value = {
            "candidate": CANDIDATE,
            "decision": {"success": True, "irregularity_percent": 2.0},
            "drperf_full_report": {"max_unexplained_share": 0.02},
        }
        result = evaluate_pcvs.evaluate_candidate(
            "vllm", Path("/tmp/root/vllm-005"), CANDIDATE
        )
        self.assertEqual(result["accepted_candidate"], CANDIDATE)
        self.assertTrue(result["decision"]["success"])
        self.assertIn("drperf_full_report", result)


if __name__ == "__main__":
    unittest.main()
