from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import full_feedback


REPORT = {
    "case_id": "vllm-001",
    "iteration": 1,
    "candidate": {"pcvs": []},
    "drperf_full_report": {
        "states": [{"calls": 3}],
        "formula": {"coefficients": {"items": 2.0}},
        "gate_reasons": ["example internal reason"],
    },
    "script_decision": {
        "assessment": {
            "valid": True,
            "success": False,
            "irregularity_percent": 17.25,
        }
    },
}


class ScalarFeedbackTests(unittest.TestCase):
    def test_agent_visible_feedback_contains_only_percentage(self):
        self.assertEqual(
            full_feedback._agent_visible_feedback(REPORT, "scalar"),
            {"irregularity_percent": 17.25},
        )

    def test_unscorable_measurement_returns_sanitized_diagnostics(self):
        report = {
            "script_decision": {
                "assessment": {
                    "valid": False,
                    "irregularity_percent": None,
                    "reasons": ["insufficient state points: 2; need 4"],
                }
            }
        }
        self.assertIsNone(full_feedback._scalar_irregularity(report))
        self.assertEqual(
            full_feedback._agent_visible_feedback(report, "scalar"),
            {
                "status": "invalid",
                "reasons": ["insufficient state points: 2; need 4"],
            },
        )

    def test_invalid_retry_prompt_exposes_reason_but_no_full_report(self):
        report = {
            "script_decision": {
                "assessment": {
                    "valid": False,
                    "irregularity_percent": None,
                    "reasons": ["insufficient state points: 2; need 4"],
                }
            },
            "drperf_full_report": {"states": [{"state": {"secret": 7}}]},
        }
        prompt = full_feedback._turn_prompt(
            "vllm-001", Path("/unused"), 2, report, "scalar"
        )
        self.assertIn("previous measurement was invalid", prompt)
        self.assertIn("insufficient state points: 2; need 4", prompt)
        self.assertNotIn("secret", prompt)
        self.assertNotIn("drperf_full_report", prompt)

    def test_retry_prompt_leaks_no_full_report_fields(self):
        prompt = full_feedback._turn_prompt(
            "vllm-001", Path("/unused"), 2, REPORT, "scalar"
        )
        self.assertIn("Previous irregularity: 17.25%", prompt)
        for forbidden in (
            '"states"', '"calls"', '"formula"', '"coefficients"', '"gate_reasons"',
            "example internal reason", "drperf_full_report",
        ):
            self.assertNotIn(forbidden, prompt)

    @patch("full_feedback.strict_wan._file_blocks", return_value="\nCASE DATA")
    def test_initial_prompt_has_context_but_no_previous_results(self, blocks):
        prompt = full_feedback._turn_prompt(
            "vllm-001", Path("/isolated"), 1, None, "scalar"
        )
        blocks.assert_called_once_with(Path("/isolated"))
        self.assertIn("CASE: vllm-001", prompt)
        self.assertIn("CASE DATA", prompt)
        self.assertNotIn("Previous irregularity", prompt)

    def test_scalar_protocol_name_is_distinct(self):
        self.assertEqual(
            full_feedback._protocol("scalar"),
            "scalar-irregularity-with-validation-feedback-scripted-measurement",
        )

    def test_protocol_guard_rejects_legacy_invalid_penalty(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempt = root / "vllm-001" / "iterations" / "iteration-001"
            attempt.mkdir(parents=True)
            (attempt / "agent-visible-feedback.json").write_text(
                json.dumps({"irregularity_percent": 100.0})
            )
            (attempt / "script-decision.json").write_text(json.dumps({
                "assessment": {"valid": False, "irregularity_percent": None}
            }))
            with self.assertRaisesRegex(
                full_feedback.FullFeedbackError, "legacy 100%-for-invalid"
            ):
                full_feedback._ensure_protocol(root, "vllm", "scalar")

    def test_protocol_guard_stamps_fresh_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            full_feedback._ensure_protocol(root, "accidental-quadratic", "scalar")
            protocol = json.loads((root / "experiment-protocol.json").read_text())
            self.assertEqual(
                protocol["agent_feedback_schema"],
                "score-or-sanitized-invalid-v2",
            )


if __name__ == "__main__":
    unittest.main()
