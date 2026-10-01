import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import core
import strict_wan


class StrictWanTests(unittest.TestCase):
    def test_iteration_limit_is_ten(self):
        self.assertEqual(strict_wan.MAX_ITERATIONS, 10)

    def test_agent_model_can_be_pinned(self):
        with patch.dict(os.environ, {"DRPERF_AGENT_MODEL": "gpt-6-astra"}):
            command = strict_wan._codex_base(strict_wan.CANDIDATE_SCHEMA)
        self.assertIn("--model", command)
        self.assertEqual(command[command.index("--model") + 1], "gpt-6-astra")

    def test_event_parser_rejects_tool_actions(self):
        events = "\n".join((
            json.dumps({"type": "thread.started", "thread_id": "abc"}),
            json.dumps({"type": "item.completed", "item": {"type": "command_execution"}}),
        ))
        with self.assertRaisesRegex(strict_wan.StrictWanError, "non-message action"):
            strict_wan._parse_codex_events(events)

    def test_event_parser_accepts_structured_agent_message(self):
        events = "\n".join((
            json.dumps({"type": "thread.started", "thread_id": "abc"}),
            json.dumps({"type": "item.completed", "item": {"type": "error"}}),
            json.dumps({
                "type": "item.completed",
                "item": {"type": "agent_message", "text": '{"success":true}'},
            }),
        ))
        thread, value = strict_wan._parse_codex_events(events)
        self.assertEqual(thread, "abc")
        self.assertEqual(value, {"success": True})

    def test_expression_guard_rejects_filesystem_and_dunder_access(self):
        for expression in (
            "open(\"secret\")", "value.__class__", "os.system(\"id\")",
            "__import__('os')",
        ):
            with self.subTest(expression=expression):
                with self.assertRaises(strict_wan.StrictWanError):
                    strict_wan._validate_expression(expression)

    def test_expression_guard_allows_derived_state(self):
        expression = "x.numel() * int(flag) + len(cache)"
        self.assertEqual(strict_wan._validate_expression(expression), expression)
        mapping = "self.__dict__.get('_cache', ())"
        self.assertEqual(strict_wan._validate_expression(mapping), mapping)
        storage = "self.__dict__.__sizeof__()"
        self.assertEqual(strict_wan._validate_expression(storage), storage)
        gc_state = "__import__('gc').get_count()[0]"
        self.assertEqual(strict_wan._validate_expression(gc_state), gc_state)
        stride = "x.stride()[2]"
        self.assertEqual(strict_wan._validate_expression(stride), stride)
        contiguous = "int(x.is_contiguous())"
        self.assertEqual(strict_wan._validate_expression(contiguous), contiguous)
        bounded_sum = "sum(x * i for i in range(len(widths)))"
        self.assertEqual(
            strict_wan._validate_expression(bounded_sum),
            "sum((x * i for i in range(len(widths))))",
        )

    def test_measurer_prompt_defines_numeric_unscoreable_penalty(self):
        prompt = strict_wan._measurer_prompt({"states": []}, True)
        self.assertIn("100.0", prompt)
        self.assertIn("unscoreable", prompt)

    def test_fresh_agent_workdir_removes_stale_cross_run_files(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            strict_wan.tempfile, "gettempdir", return_value=temporary
        ):
            path = strict_wan._agent_cwd("scalar-feedback-vllm-001", "agent-PCVs")
            (path / "stale-result.json").write_text("must not be visible")
            reset = strict_wan._agent_cwd(
                "scalar-feedback-vllm-001", "agent-PCVs", reset=True
            )
            self.assertEqual(path, reset)
            self.assertEqual(list(reset.iterdir()), [])

    def test_unscoreable_agent_mismatch_is_normalized(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "run"
            core.start("wan-001", run)
            state = core.load_state(run)
            state["attempts"] = [{
                "iteration": 1,
                "candidate": {"pcvs": []},
                "measurement_runs": [{
                    "assessment": {
                        "valid": False,
                        "irregularity_percent": 0.0,
                    }
                }],
                "outcome": "invalid",
                "irregularity_percent": 0.0,
            }]
            core.save_state(run, state)
            strict = strict_wan._strict_state(run)
            with patch.object(strict_wan, "_measurement_payload", return_value={}), patch.object(
                strict_wan,
                "_agent_turn",
                return_value=(
                    "agent-2-thread",
                    {"irregularity_percent": 0.0, "success": True},
                ),
            ), patch.object(strict_wan, "_case_report"):
                score, success = strict_wan._score_last_attempt(run, strict)
            self.assertEqual(score, 100.0)
            self.assertFalse(success)
            self.assertEqual(strict["normalized_unscoreable_turns"], [1])

    def test_apply_candidate_replaces_marker_and_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "run"
            core.start("wan-001", run)
            state = core.load_state(run)
            source = run / "selector" / "workspace" / state["source_path"]
            candidate = {
                "iteration": 1,
                "pcvs": [{
                    "name": "n",
                    "expression": "image.numel()",
                    "rationale": "Elementwise work.",
                }],
                "hypothesis": "instructions = a*n + constant",
            }
            strict_wan._apply_candidate(run, candidate, 1)
            self.assertIn("n=(image.numel())", source.read_text())
            self.assertEqual(core.read_json(run / "selector/workspace/CANDIDATE.json"), candidate)


if __name__ == "__main__":
    unittest.main()
