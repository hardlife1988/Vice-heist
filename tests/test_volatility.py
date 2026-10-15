import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'math'))
from analyze_volatility import distribution


class VolatilityTests(unittest.TestCase):
    def test_weights_cost_and_inclusive_tail_boundaries(self):
        # 50% zero, 25% 100x, 25% 200x, with a 100x buy cost.
        result = distribution({0: 2, 10000: 1, 20000: 1}, 100)
        self.assertEqual(result['mean_x'], 75)
        self.assertEqual(result['median_x'], 0)
        self.assertEqual(result['mean_positive_win_x'], 150)
        self.assertEqual(result['below_cost_probability'], .5)
        self.assertEqual(result['break_even_probability'], .25)
        self.assertEqual(result['profit_probability'], .25)
        self.assertEqual(result['tails_at_least_x']['100'], .5)
        self.assertEqual(result['tails_at_least_x']['500'], 0)
        self.assertAlmostEqual(result['standard_deviation_x'], 82.915619758885)
        self.assertAlmostEqual(result['standard_deviation_per_cost'], .82915619758885)

    def test_cap_boundary_and_empty_conditional_distribution(self):
        result = distribution({0: 999999, 1000000: 1})
        self.assertEqual(result['tails_at_least_x']['10000'], .000001)
        self.assertEqual(result['maximum_x'], 10000)
        self.assertIsNone(distribution({}))


if __name__ == '__main__':
    unittest.main()
