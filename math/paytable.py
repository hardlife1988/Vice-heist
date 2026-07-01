"""
Paytable module for Vice-heist slot game.
Defines symbol values, paylines, and win combinations.
"""

from enum import Enum


class Symbol(Enum):
    """Symbol definitions for Vice-heist."""
    WILD = 'W'           # 10x value
    SCATTER = 'S'        # Trigger free spins
    BOOK = 'B'           # 5x value (expanding symbol)
    GOLD_BAR = 'G'       # 4x value
    DIAMOND = 'D'        # 3x value
    RUBY = 'R'           # 2x value
    EMERALD = 'E'        # 1.5x value
    CLUB = 'C'           # 1x value
    SPADE = 'P'          # 0.5x value
    HEART = 'H'          # 0.5x value


class Paytable:
    """Paytable for Vice-heist slot game."""
    
    # Symbol values per coin (for 5 of a kind)
    SYMBOL_VALUES = {
        Symbol.WILD: 10,
        Symbol.BOOK: 5,
        Symbol.GOLD_BAR: 4,
        Symbol.DIAMOND: 3,
        Symbol.RUBY: 2,
        Symbol.EMERALD: 1.5,
        Symbol.CLUB: 1,
        Symbol.SPADE: 0.5,
        Symbol.HEART: 0.5,
    }
    
    # Payline definitions (5 reels, 3 rows)
    PAYLINES = {
        1: [1, 1, 1, 1, 1],  # Middle line
        2: [0, 0, 0, 0, 0],  # Top line
        3: [2, 2, 2, 2, 2],  # Bottom line
        4: [0, 1, 2, 1, 0],  # V shape down
        5: [2, 1, 0, 1, 2],  # V shape up
        6: [0, 0, 1, 0, 0],  # W shape
        7: [2, 2, 1, 2, 2],  # Inverted W
        8: [0, 1, 1, 1, 0],  # Mountain
        9: [2, 1, 1, 1, 2],  # Valley
        10: [1, 0, 1, 0, 1], # Zigzag
    }
    
    @staticmethod
    def get_payline(payline_num):
        """Get payline row positions."""
        return Paytable.PAYLINES.get(payline_num, [])
    
    @staticmethod
    def calculate_win(symbol, match_count, bet_amount, multiplier=1.0):
        """
        Calculate win amount for a matching combination.
        
        Args:
            symbol: Symbol that matched
            match_count: Number of matching symbols (typically 3-5)
            bet_amount: Bet amount per line
            multiplier: Feature multiplier (e.g., free spins 2x)
            
        Returns:
            float: Win amount
        """
        if match_count < 3:
            return 0
        
        if symbol == Symbol.SCATTER:
            # Scatter doesn't pay from paylines, only triggers features
            return 0
        
        base_value = Paytable.SYMBOL_VALUES.get(symbol, 0)
        
        # Win calculation: base_value * match_count * bet_amount * multiplier
        win = base_value * match_count * bet_amount * multiplier
        
        return win
    
    @staticmethod
    def get_symbol_name(symbol):
        """Get human-readable symbol name."""
        names = {
            Symbol.WILD: "Wild",
            Symbol.SCATTER: "Book (Scatter)",
            Symbol.BOOK: "Book",
            Symbol.GOLD_BAR: "Gold Bar",
            Symbol.DIAMOND: "Diamond",
            Symbol.RUBY: "Ruby",
            Symbol.EMERALD: "Emerald",
            Symbol.CLUB: "Club",
            Symbol.SPADE: "Spade",
            Symbol.HEART: "Heart",
        }
        return names.get(symbol, "Unknown")
