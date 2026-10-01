"""Run with: python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "math"))
from game_config import GameConfig
from paytable import Symbol
from win_evaluator import WinEvaluator

W, G, S, H = Symbol.WILD, Symbol.GOLD_BAR, Symbol.SCATTER, Symbol.HEART


def grid_with_middle_line(symbols):
    grid = [[H] * 5 for _ in range(3)]
    grid[1] = symbols
    return grid


class WinEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = WinEvaluator(GameConfig())

    def test_leading_wilds_choose_highest_pay(self):
        line = [W, W, W, G, G]
        result = self.evaluator._evaluate_payline(
            grid_with_middle_line(line), [1] * 5, 1, 1
        )
        self.assertEqual(result["symbol_key"], "G")
        self.assertEqual(result["count"], 5)
        self.assertEqual(result["win"], 7.43)

    def test_all_wild_line(self):
        result = self.evaluator._evaluate_payline(
            grid_with_middle_line([W] * 5), [1] * 5, 1, 1
        )
        self.assertEqual(result["symbol_key"], "W")
        self.assertEqual(result["win"], 79.5)

    def test_scatter_triggers(self):
        grid = [[H] * 5 for _ in range(3)]
        grid[0][0] = grid[0][1] = grid[0][2] = S
        result = self.evaluator.evaluate_spin(grid, 1)
        self.assertEqual(result["scatter_count"], 3)
        self.assertEqual(result["scatter_win"], 2)
        self.assertTrue(result["triggers_free_spins"])

    def test_invalid_grid(self):
        with self.assertRaises(ValueError):
            self.evaluator.evaluate_spin([[H] * 5], 1)


if __name__ == "__main__":
    unittest.main()
