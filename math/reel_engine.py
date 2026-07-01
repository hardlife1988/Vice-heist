"""
Reel Engine for Vice-heist slot game.
Manages reel spin logic and symbol distributions.
"""

import random
from math import ceil
from paytable import Symbol


class ReelWeights:
    """Symbol weights for each reel in Vice-heist."""
    
    # Reel 1 (leftmost)
    REEL_1 = {
        Symbol.WILD: 15,
        Symbol.BOOK: 8,
        Symbol.GOLD_BAR: 12,
        Symbol.DIAMOND: 15,
        Symbol.RUBY: 18,
        Symbol.EMERALD: 12,
        Symbol.CLUB: 10,
        Symbol.SPADE: 10,
        Symbol.HEART: 10,
    }
    
    # Reel 2
    REEL_2 = {
        Symbol.WILD: 12,
        Symbol.BOOK: 10,
        Symbol.GOLD_BAR: 15,
        Symbol.DIAMOND: 14,
        Symbol.RUBY: 16,
        Symbol.EMERALD: 14,
        Symbol.CLUB: 10,
        Symbol.SPADE: 12,
        Symbol.HEART: 11,
    }
    
    # Reel 3 (middle)
    REEL_3 = {
        Symbol.WILD: 20,  # Higher wild in middle
        Symbol.BOOK: 12,
        Symbol.GOLD_BAR: 12,
        Symbol.DIAMOND: 14,
        Symbol.RUBY: 14,
        Symbol.EMERALD: 12,
        Symbol.CLUB: 10,
        Symbol.SPADE: 10,
        Symbol.HEART: 10,
    }
    
    # Reel 4
    REEL_4 = {
        Symbol.WILD: 12,
        Symbol.BOOK: 10,
        Symbol.GOLD_BAR: 15,
        Symbol.DIAMOND: 14,
        Symbol.RUBY: 16,
        Symbol.EMERALD: 14,
        Symbol.CLUB: 10,
        Symbol.SPADE: 12,
        Symbol.HEART: 11,
    }
    
    # Reel 5 (rightmost)
    REEL_5 = {
        Symbol.WILD: 15,
        Symbol.BOOK: 8,
        Symbol.GOLD_BAR: 12,
        Symbol.DIAMOND: 15,
        Symbol.RUBY: 18,
        Symbol.EMERALD: 12,
        Symbol.CLUB: 10,
        Symbol.SPADE: 10,
        Symbol.HEART: 10,
    }
    
    ALL_REELS = [REEL_1, REEL_2, REEL_3, REEL_4, REEL_5]


class ReelEngine:
    """Manages reel spins and symbol generation."""
    
    def __init__(self, config):
        self.config = config
        self.reels = config.reels  # 5
        self.rows = config.rows    # 3
    
    def spin_reels(self):
        """
        Spin all reels and return result.
        
        Returns:
            list: 5x3 grid of symbols
                Format: [[row0_reel0, row0_reel1, ...], ...]
        """
        reel_result = []
        
        for reel_num in range(self.reels):
            reel_symbols = self._spin_single_reel(reel_num)
            reel_result.append(reel_symbols)
        
        # Transpose to row-based format
        result_grid = []
        for row in range(self.rows):
            row_symbols = []
            for reel in range(self.reels):
                row_symbols.append(reel_result[reel][row])
            result_grid.append(row_symbols)
        
        return result_grid
    
    def _spin_single_reel(self, reel_num):
        """
        Spin a single reel.
        
        Args:
            reel_num: Reel number (0-4)
            
        Returns:
            list: 3 symbols for this reel
        """
        weights = ReelWeights.ALL_REELS[reel_num]
        symbols = list(weights.keys())
        weight_values = list(weights.values())
        total_weight = sum(weight_values)
        
        reel_symbols = []
        for _ in range(self.rows):
            # Weighted random selection
            symbol = random.choices(symbols, weights=weight_values, k=1)[0]
            reel_symbols.append(symbol)
        
        return reel_symbols
    
    def get_reel_result_display(self, reel_result):
        """
        Format reel result for display.
        
        Args:
            reel_result: Grid of symbols
            
        Returns:
            str: Formatted reel result
        """
        display = ""
        for row in reel_result:
            display += " ".join([s.value for s in row]) + "\n"
        return display
