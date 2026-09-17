"""Tests of experiment acceptance rules; synthetic data is not case evidence."""
import unittest
from unittest.mock import patch

import measure


class GateTests(unittest.TestCase):
    def analyze(self, values, counts, warnings=()):
        keys = {i: {'region': 'target', 'states': [('n', n)], 'overflow': False,
                    'count': 1, 'vec': {0: count}, 'root': 'target'}
                for i, (n, count) in enumerate(zip(values, counts))}
        with patch.object(measure.runner, 'load_runs', return_value={'runs': []}), \
             patch.object(measure.runner, 'validity', return_value=list(warnings)), \
             patch.object(measure.runner, 'blocks_of_set', return_value=(keys, {0: ('test', 'work', None)})), \
             patch.object(measure.runner, 'demangle_slots', side_effect=lambda x: x), \
             patch.object(measure.runner, 'load_traces_all', return_value=[]):
            return measure.analyze('/unused', 'target')[0]

    def test_affine_cost_qualifies(self):
        data = self.analyze([1, 2, 3, 4], [1100, 2100, 3100, 4100])
        self.assertTrue(data['gate_pass'])
        self.assertAlmostEqual(data['formula']['coefficients']['n'], 1000)

    def test_single_state_is_not_an_explanation(self):
        data = self.analyze([1], [1100])
        self.assertFalse(data['gate_pass'])
        self.assertFalse(data['sufficient_points'])

    def test_irregular_cost_fails(self):
        data = self.analyze([1, 2, 3], [1000, 10000, 1000])
        self.assertFalse(data['gate_pass'])
        self.assertGreater(data['max_unexplained_share'], 0.05)

    def test_invalid_counts_never_qualify(self):
        data = self.analyze([1, 2, 3], [1100, 2100, 3100], ['counter overflow'])
        self.assertFalse(data['gate_pass'])
        self.assertIn('counter overflow', data['gate_reasons'])

    def test_absent_target_fails(self):
        data = self.analyze([], [])
        self.assertFalse(data['gate_pass'])
        self.assertEqual(data['calls'], 0)


if __name__ == '__main__':
    unittest.main()
