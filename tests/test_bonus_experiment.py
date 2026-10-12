"""Candidate calibration, integer conservation, and source integrity regressions."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'math'))
from experiment_bonus_distribution import apportion, candidate_weights, metrics, verify_inputs, run


class BonusExperimentTests(unittest.TestCase):
    def setUp(self):
        payouts = [0, 10000, 3200, 10, 20, 50, 80, 100, 120, 200, 300, 500, 1000]
        self.rows = np.array([(i + 1, 10 if i < 3 else 100000000, p * 100)
                              for i, p in enumerate(payouts)], dtype=np.int64)
        self.reserved = np.arange(len(payouts)) < 3

    def test_candidates_conserve_reserved_mass_and_hit_both_targets(self):
        for target in (.30, .35, .40):
            with self.subTest(target=target):
                weights, result = candidate_weights(self.rows, self.reserved, target)
                self.assertAlmostEqual(result['rtp'], .96, places=6)
                self.assertEqual(int(weights.sum()), int(self.rows[:, 1].sum()))
                np.testing.assert_array_equal(weights[self.reserved], self.rows[self.reserved, 1])
                self.assertTrue(np.all(weights > 0))
                self.assertAlmostEqual(weights[self.rows[:, 2] >= 10000].sum() / weights.sum(), target, places=6)
                second, second_result = candidate_weights(self.rows, self.reserved, target)
                np.testing.assert_array_equal(weights, second)
                self.assertEqual(result, second_result)

    def test_apportionment_stable_ties_and_mass(self):
        np.testing.assert_array_equal(apportion(np.array([1.5, 1.5, 2.0]), 5), [2, 1, 2])
        with self.assertRaises(ValueError):
            apportion(np.array([.2, .8]), 1)

    def test_inclusive_band_metrics_and_return_denominator(self):
        result = metrics(np.array([0, 5000, 30000, 500000, 1000000]), np.ones(5, dtype=np.int64), 100)
        self.assertEqual(result['50_to_300_x']['probability'], .4)
        self.assertEqual(result['5000_to_10000_x']['probability'], .4)
        self.assertAlmostEqual(result['50_to_300_x']['share_of_return'], 35000 / 1535000)

    def test_source_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            hashes = {}
            for mode in ('base', 'bonus'):
                for prefix, extension in [('books', 'jsonl.zst'), ('lookUpTable', 'csv')]:
                    name = f'{prefix}_{mode}.{extension}'
                    (folder / name).write_bytes(b'verified fixture')
                    hashes[name] = hashlib.sha256(b'verified fixture').hexdigest()
            report = folder / 'baseline.json'
            report.write_text(json.dumps({'input_sha256': hashes}))
            self.assertEqual(verify_inputs(folder, report), hashes)
            (folder / 'lookUpTable_bonus.csv').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_inputs(folder, report)

    def test_output_cannot_overlap_production_source(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for output in (folder, folder / 'candidate', folder.parent):
                with self.subTest(output=output), self.assertRaisesRegex(ValueError, 'isolated'):
                    run(folder, folder / 'missing_report', output)


if __name__ == '__main__':
    unittest.main()
