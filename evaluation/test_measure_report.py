from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "drperf_measure", ROOT / "bench_anontated" / "measure.py"
)
assert SPEC is not None and SPEC.loader is not None
measure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(measure)


class BreakdownTests(unittest.TestCase):
    def test_complete_function_breakdown_is_sorted_and_normalized(self):
        class Regime:
            n_irr = 7
            by_sym_irr = {
                ("mod-a", "small"): 20.0,
                ("mod-b", "large"): 80.0,
            }

        result = measure.irregularity_breakdown(Regime())
        self.assertEqual(result["irregular_basic_blocks"], 7)
        self.assertEqual(result["total_irregular_instructions_per_call"], 100.0)
        self.assertEqual(
            [item["function"] for item in result["functions"]],
            ["large", "small"],
        )
        self.assertEqual(
            [item["share_of_irregular_instructions"] for item in result["functions"]],
            [0.8, 0.2],
        )

    def test_empty_breakdown_is_explicit(self):
        result = measure.irregularity_breakdown(None)
        self.assertEqual(result["irregular_basic_blocks"], 0)
        self.assertEqual(result["functions"], [])


if __name__ == "__main__":
    unittest.main()
