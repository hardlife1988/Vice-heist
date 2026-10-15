"""Natural transfers must preserve exact mass/return, triggers and cap weights."""
import sys
import unittest
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'math'))
from experiment_natural_distribution import natural_candidate, paid_sum, apportion_delta, repair_return


class NaturalExperimentTests(unittest.TestCase):
    def setUp(self):
        # Add an untouched zero-payout base book so the fixture is exactly 96%.
        payout = [1000000, 600200, 10200, 200, 220, 10]
        weights = [100, 4000, 1000000, 10000000, 10000000, 0]
        for adjustment in range(1, 97):
            weights[-1] = adjustment
            needed = paid_sum(payout, weights) - 96 * sum(weights)
            if needed % 96 == 0:
                break
        zero_weight = needed // 96
        self.rows = np.array([(i + 1, w, p) for i, (w, p) in enumerate(
            zip([zero_weight] + weights, [0] + payout))], dtype=np.int64)
        self.free = np.array([0, 999800, 600000, 10000, 0, 20, 0], dtype=np.int64)
        self.trigger = np.array([False, True, True, True, True, True, False])

    def test_exact_return_mass_cap_trigger_and_medium_frequency(self):
        for fraction in (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)):
            with self.subTest(fraction=fraction):
                original = self.rows[:, 1]
                weights, result = natural_candidate(self.rows, self.free, self.trigger, fraction)
                self.assertEqual(sum(map(int, weights)), sum(map(int, original)))
                self.assertEqual(paid_sum(self.rows[:, 2], weights), paid_sum(self.rows[:, 2], original))
                self.assertEqual(result['rtp'], .96)
                self.assertEqual(weights[self.trigger].sum(), original[self.trigger].sum())
                self.assertEqual(weights[1], original[1])  # Cap remains reserved.
                np.testing.assert_array_equal(weights[~self.trigger], original[~self.trigger])
                self.assertGreater(weights[3], original[3])  # 100x free-spin outcome.
                self.assertLess(weights[2], original[2])  # Eligible extreme donor.
                self.assertTrue(np.all(weights > 0))
                second, metadata = natural_candidate(self.rows, self.free, self.trigger, fraction)
                np.testing.assert_array_equal(second, weights)
                self.assertEqual(metadata, result)

    def test_cap_cannot_substitute_for_noncap_donor(self):
        rows = self.rows.copy()
        rows[2, 2] = 1000000
        free = self.free.copy()
        free[2] = 999800
        with self.assertRaisesRegex(ValueError, 'pool is empty'):
            natural_candidate(rows, free, self.trigger, Fraction(1, 2))

    def test_insufficient_low_mass_fails_without_broadening_pool(self):
        rows = self.rows.copy()
        rows[4:6, 1] = 1
        with self.assertRaisesRegex(ValueError, 'exhaust low'):
            natural_candidate(rows, self.free, self.trigger, Fraction(3, 4))

    def test_exact_apportionment_large_integers_and_stable_ties(self):
        np.testing.assert_array_equal(apportion_delta([1, 1, 2], 5), [1, 1, 3])
        result = apportion_delta([10**12 + 1, 10**12 + 2, 10**12 + 3], 10**12 + 5)
        self.assertEqual(sum(map(int, result)), 10**12 + 5)
        self.assertTrue(np.all(result >= 0))

    def test_return_repair_is_mass_neutral_and_rejects_infeasible_quantum(self):
        weights = np.array([100, 100], dtype=np.int64)
        repair_return(np.array([200, 220]), weights, np.array([True, True]), 40)
        np.testing.assert_array_equal(weights, [98, 102])
        with self.assertRaisesRegex(ValueError, 'infeasible'):
            repair_return(np.array([200, 220]), weights, np.array([True, True]), 6)


if __name__ == '__main__':
    unittest.main()
