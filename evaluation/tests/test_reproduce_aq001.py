import os
import unittest
from unittest.mock import patch

from evaluation.reproduce_aq001 import ENV_PREFIX, FEATURE, compare, extra_environment
from evaluation.results import EvaluationError


def run(label, values, counts):
    return {"label": label, "calls": [
        {"state": {FEATURE: value}, "instructions": count}
        for value, count in zip(values, counts)]}


class CountComparisonTests(unittest.TestCase):
    def test_compares_raw_counts_by_call_including_repeated_values(self):
        rows = compare([run("A", [0, 1, 0], [10, 20, 30]),
                        run("B", [0, 1, 0], [11, 20, 35])])
        self.assertEqual(rows, [
            {"call": 1, FEATURE: 0, "A": 10, "B": 11},
            {"call": 2, FEATURE: 1, "A": 20, "B": 20},
            {"call": 3, FEATURE: 0, "A": 30, "B": 35}])

    def test_rejects_different_values_order_or_call_count(self):
        reference = run("A", [0, 1, 0], [10, 20, 30])
        for values in ([0, 2, 0], [0, 0, 1], [0, 1]):
            with self.subTest(values=values), self.assertRaisesRegex(EvaluationError, "call order"):
                compare([reference, run("B", values, [11, 20, 35])])

    def test_environment_condition_is_restored_even_after_failure(self):
        with patch.dict(os.environ, {f"{ENV_PREFIX}99": "original"}):
            original = dict(os.environ)
            with self.assertRaisesRegex(RuntimeError, "measurement failed"):
                with extra_environment(2):
                    added = {k: v for k, v in os.environ.items() if k.startswith(ENV_PREFIX)}
                    self.assertEqual(added, {f"{ENV_PREFIX}0": "padding", f"{ENV_PREFIX}1": "padding"})
                    self.assertEqual({k: v for k, v in os.environ.items() if not k.startswith(ENV_PREFIX)},
                                     {k: v for k, v in original.items() if not k.startswith(ENV_PREFIX)})
                    raise RuntimeError("measurement failed")
            self.assertEqual(dict(os.environ), original)
            with extra_environment(0):
                self.assertFalse(any(k.startswith(ENV_PREFIX) for k in os.environ))
            self.assertEqual(dict(os.environ), original)


if __name__ == "__main__":
    unittest.main()
