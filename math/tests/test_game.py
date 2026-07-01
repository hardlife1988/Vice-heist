"""
Unit tests for Vice-heist game mechanics.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from paytable import Symbol, Paytable
from game_config import GameConfig
from reel_engine import ReelEngine
from win_evaluator import WinEvaluator
from gamestate import GameState


class TestPaytable(unittest.TestCase):
    """Test paytable calculations."""
    
    def test_symbol_values_exist(self):
        """Test that all symbols have defined values."""
        for symbol in [Symbol.WILD, Symbol.BOOK, Symbol.GOLD_BAR, Symbol.DIAMOND]:
            self.assertIn(symbol, Paytable.SYMBOL_VALUES)
    
    def test_calculate_win_5_of_a_kind(self):
        """Test 5 of a kind calculation."""
        win = Paytable.calculate_win(Symbol.WILD, 5, 1.0)
        # 10 * 5 * 1.0 * 1.0 = 50
        self.assertEqual(win, 50)
    
    def test_calculate_win_3_of_a_kind(self):
        """Test 3 of a kind calculation."""
        win = Paytable.calculate_win(Symbol.DIAMOND, 3, 1.0)
        # 3 * 3 * 1.0 * 1.0 = 9
        self.assertEqual(win, 9)
    
    def test_calculate_win_with_multiplier(self):
        """Test win calculation with multiplier (free spins)."""
        win = Paytable.calculate_win(Symbol.GOLD_BAR, 4, 1.0, 2.0)
        # 4 * 4 * 1.0 * 2.0 = 32
        self.assertEqual(win, 32)
    
    def test_scatter_no_payline_win(self):
        """Test that scatter doesn't win from paylines."""
        win = Paytable.calculate_win(Symbol.SCATTER, 5, 1.0)
        self.assertEqual(win, 0)
    
    def test_less_than_3_no_win(self):
        """Test that less than 3 matches is no win."""
        win = Paytable.calculate_win(Symbol.WILD, 2, 1.0)
        self.assertEqual(win, 0)
    
    def test_payline_positions(self):
        """Test payline definitions."""
        payline_1 = Paytable.get_payline(1)
        self.assertEqual(payline_1, [1, 1, 1, 1, 1])  # Middle line
    
    def test_symbol_names(self):
        """Test symbol name retrieval."""
        self.assertEqual(Paytable.get_symbol_name(Symbol.WILD), "Wild")
        self.assertEqual(Paytable.get_symbol_name(Symbol.DIAMOND), "Diamond")


class TestReelEngine(unittest.TestCase):
    """Test reel engine functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = GameConfig()
        self.engine = ReelEngine(self.config)
    
    def test_spin_returns_correct_dimensions(self):
        """Test that spin returns 3x5 grid."""
        result = self.engine.spin_reels()
        self.assertEqual(len(result), 3)  # 3 rows
        self.assertEqual(len(result[0]), 5)  # 5 reels
    
    def test_spin_returns_valid_symbols(self):
        """Test that spin returns valid Symbol enum values."""
        result = self.engine.spin_reels()
        for row in result:
            for symbol in row:
                self.assertIsInstance(symbol, Symbol)
    
    def test_multiple_spins_vary(self):
        """Test that multiple spins produce different results."""
        spin1 = self.engine.spin_reels()
        spin2 = self.engine.spin_reels()
        # Statistically should be different (very low chance of same result)
        self.assertNotEqual(spin1, spin2)


class TestWinEvaluator(unittest.TestCase):
    """Test win evaluation logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = GameConfig()
        self.evaluator = WinEvaluator(self.config)
    
    def test_no_win_all_different(self):
        """Test that no matching symbols = no win."""
        # All different symbols
        grid = [
            [Symbol.DIAMOND, Symbol.RUBY, Symbol.CLUB, Symbol.SPADE, Symbol.HEART],
            [Symbol.EMERALD, Symbol.DIAMOND, Symbol.RUBY, Symbol.CLUB, Symbol.SPADE],
            [Symbol.HEART, Symbol.EMERALD, Symbol.DIAMOND, Symbol.RUBY, Symbol.CLUB],
        ]
        result = self.evaluator.evaluate_spin(grid, 1.0)
        self.assertEqual(result['total_win'], 0)
    
    def test_payline_win_5_wilds(self):
        """Test payline win with 5 wilds (middle line)."""
        # Middle row all wilds
        grid = [
            [Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND],
            [Symbol.WILD, Symbol.WILD, Symbol.WILD, Symbol.WILD, Symbol.WILD],
            [Symbol.CLUB, Symbol.CLUB, Symbol.CLUB, Symbol.CLUB, Symbol.CLUB],
        ]
        result = self.evaluator.evaluate_spin(grid, 1.0)
        self.assertGreater(result['total_win'], 0)
    
    def test_scatter_trigger(self):
        """Test free spins trigger with 3 scatters."""
        # Place 3 scatters
        grid = [
            [Symbol.SCATTER, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND],
            [Symbol.DIAMOND, Symbol.SCATTER, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND],
            [Symbol.DIAMOND, Symbol.DIAMOND, Symbol.SCATTER, Symbol.DIAMOND, Symbol.DIAMOND],
        ]
        result = self.evaluator.evaluate_spin(grid, 1.0)
        self.assertTrue(result['triggers_free_spins'])
        self.assertEqual(result['scatter_count'], 3)
    
    def test_scatter_no_trigger_below_3(self):
        """Test no free spins trigger with less than 3 scatters."""
        grid = [
            [Symbol.SCATTER, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND],
            [Symbol.DIAMOND, Symbol.SCATTER, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND],
            [Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND, Symbol.DIAMOND],
        ]
        result = self.evaluator.evaluate_spin(grid, 1.0)
        self.assertFalse(result['triggers_free_spins'])
        self.assertEqual(result['scatter_count'], 2)


class TestGameState(unittest.TestCase):
    """Test game state management."""
    
    def setUp(self):
        """Set up test fixtures."""
        config = GameConfig()
        self.gamestate = GameState(config)
    
    def test_start_spin(self):
        """Test spin tracking."""
        initial_spins = self.gamestate.total_spins
        self.gamestate.start_spin(1.0)
        self.assertEqual(self.gamestate.total_spins, initial_spins + 1)
    
    def test_end_spin_win(self):
        """Test win tracking."""
        self.gamestate.start_spin(1.0)
        self.gamestate.end_spin(10.0)
        self.assertEqual(self.gamestate.total_won, 10.0)
        self.assertEqual(self.gamestate.last_win, 10.0)
    
    def test_free_spins_trigger(self):
        """Test free spins feature."""
        self.gamestate.trigger_free_spins(10)
        self.assertTrue(self.gamestate.in_free_spins)
        self.assertEqual(self.gamestate.free_spins_remaining, 10)
    
    def test_use_free_spin(self):
        """Test using free spins."""
        self.gamestate.trigger_free_spins(10)
        self.gamestate.use_free_spin()
        self.assertEqual(self.gamestate.free_spins_remaining, 9)
    
    def test_free_spins_deactivate(self):
        """Test free spins deactivate when exhausted."""
        self.gamestate.trigger_free_spins(1)
        self.gamestate.use_free_spin()
        self.assertFalse(self.gamestate.in_free_spins)
        self.assertEqual(self.gamestate.free_spins_remaining, 0)


if __name__ == '__main__':
    unittest.main()
