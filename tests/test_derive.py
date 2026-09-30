"""Regression tests for affine acceptance, including valid negative intercepts."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import derive


class AffineAcceptance(unittest.TestCase):
    slots = {0: ("tree", "descend", 0)}

    def fit(self, coordinates, counts):
        return derive.derive(dict(zip(coordinates, ({0: y} for y in counts))), self.slots, split=False)[0]

    def test_single_state_fits_observed_constant_with_many_pcvs(self):
        point = (2, 4, 0, 100, 8, 99)
        model = self.fit([point], [12345])
        self.assertEqual(model.a, [0] * len(point))
        self.assertEqual(model.c, 12345)
        self.assertEqual(model.dependent, set(range(len(point))))
        self.assertEqual(model.n_const, 1)
        self.assertEqual(model.irr_share(), 0)

    def test_two_states_fit_slope_and_intercept(self):
        model = self.fit([(2,), (7,)], [2017, 7017])
        self.assertAlmostEqual(model.a[0], 1000)
        self.assertAlmostEqual(model.c, 17)
        self.assertEqual(model.n_affine, 1)
        self.assertEqual(model.n_irr, 0)

    def test_more_pcvs_than_states_still_fit(self):
        points = [(1, 2, 99, 0), (2, 4, 99, 0)]
        model = self.fit(points, [107, 207])
        self.assertEqual(model.dependent, {1, 2, 3})
        self.assertAlmostEqual(model.a[0], 100)
        for point, count in zip(points, [107, 207]):
            self.assertAlmostEqual(model.formula(point), count)

    def test_exactly_determined_plane_fits(self):
        points = [(0, 0), (1, 0), (0, 1)]
        model = self.fit(points, [7, 107, 207])
        self.assertFalse(model.dependent)
        self.assertAlmostEqual(model.a[0], 100)
        self.assertAlmostEqual(model.a[1], 200)
        self.assertAlmostEqual(model.c, 7)

    def test_no_pcvs_fits_constant(self):
        model = self.fit([()], [9876])
        self.assertEqual(model.a, [])
        self.assertEqual(model.c, 9876)
        self.assertEqual(model.n_const, 1)

    def test_empty_observations_still_have_no_fit(self):
        self.assertEqual(derive.derive({}, self.slots), [])
        self.assertIsNone(derive.derive_regime({}, [], self.slots))

    def test_sparse_fit_does_not_hide_contradicting_third_state(self):
        model = self.fit([(0,), (1,), (2,)], [1000, 2000, 10000])
        self.assertEqual(model.n_irr, 1)
        self.assertEqual(model.irr, {(0,): 1000, (1,): 2000, (2,): 10000})

    def test_depth_minus_one_is_affine_in_depth(self):
        depths = (1, 2, 3, 5, 8, 13)
        counts = [1024*(d-1) for d in depths]
        model = self.fit([(d,) for d in depths], counts)
        self.assertEqual(model.n_irr, 0)
        self.assertAlmostEqual(model.a[0], 1024)
        self.assertAlmostEqual(model.c, -1024)
        for d, cost in zip(depths, counts):
            self.assertAlmostEqual(model.formula((d,)), cost)
        report = derive.describe("tree", ["depth"], [model], {(d,): 1 for d in depths}, self.slots)
        self.assertNotIn("counts curve", report)

    def test_translation_preserves_acceptance_and_predictions(self):
        values = (0, 1, 3, 8, 20)
        counts = [1024*v + 19 for v in values]
        first = self.fit([(v,) for v in values], counts)
        translated = self.fit([(v+100,) for v in values], counts)
        self.assertEqual(first.n_irr, translated.n_irr)
        self.assertEqual(translated.n_irr, 0)
        for v in values:
            self.assertAlmostEqual(first.formula((v,)), translated.formula((v+100,)))

    def test_curvature_still_fails_tolerance(self):
        values = (4, 8, 16, 32, 64, 128)
        counts = [1024*v*v for v in values]
        model = self.fit([(v,) for v in values], counts)
        self.assertEqual(model.n_irr, 1)
        for v, cost in zip(values, counts):
            self.assertEqual(model.irr[(v,)], cost)

    def test_six_independent_pcvs(self):
        coefficients = (11, 23, 37, 41, 59, 61)
        values = [tuple([100]*6)]
        for j in range(6):
            for delta in (7, 31):
                point = [100]*6
                point[j] += delta
                values.append(tuple(point))
        counts = [sum(a*x for a, x in zip(coefficients, point))-1000 for point in values]
        model = self.fit(values, counts)
        self.assertEqual(model.n_irr, 0)
        self.assertFalse(model.dependent)
        for actual, expected in zip(model.a, coefficients):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(model.c, -1000)


if __name__ == "__main__":
    unittest.main()
