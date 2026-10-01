from pathlib import Path
import tempfile
import unittest

import core
import generic_suite


class GenericSuiteTests(unittest.TestCase):
    def test_lists_all_non_specialized_suites(self):
        self.assertEqual(len(generic_suite.list_cases("accidental-quadratic")), 21)
        self.assertEqual(
            generic_suite.list_cases("growth-multifold"),
            ["aq-003", "vllm-024"],
        )
        self.assertEqual(len(generic_suite.list_cases("v8-interpreter")), 50)
        self.assertEqual(len(generic_suite.list_cases("v8-regexp")), 28)

    def test_v8_is_explicitly_unavailable_without_built_adapter(self):
        self.assertIn(
            "blocked-runtime",
            generic_suite.unavailable_reason("v8-interpreter"),
        )

    def test_growth_staging_uses_specialized_workload_and_empty_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary) / "staged"
            generic_suite._stage_growth_case("aq-003", staged)
            manifest = core.read_json(staged / "case.json")
            source = staged / manifest["source"]["path"]
            text = source.read_text()
            self.assertIn("with perfmark.region('aq-003'):", text)
            self.assertNotIn("input_pairs=", text)
            self.assertTrue((staged / "tests" / "test_scale.py").is_file())


if __name__ == "__main__":
    unittest.main()
