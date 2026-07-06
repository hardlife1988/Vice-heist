"""
Paytable module for Vice-heist slot game.
Defines symbol values, paylines, and win combinations.
"""

from enum import Enum


class Symbol(Enum):
    """Symbol definitions for Vice-heist."""
    WILD    = 'W'   # Substitutes any non-scatter; highest payer
    SCATTER = 'S'   # Book scatter — triggers free spins (any position)
    BOOK    = 'B'   # Expanding symbol in free spins
    GOLD_BAR = 'G'
    DIAMOND  = 'D'
    RUBY     = 'R'
    EMERALD  = 'E'
    CLUB     = 'C'
    SPADE    = 'P'
    HEART    = 'H'


class Paytable:
    """Paytable for Vice-heist slot game (5 reels, 3 rows, 20 paylines)."""

    # Win multipliers for 3 / 4 / 5 of a kind (relative to total bet)
    # Format: {Symbol: {3: x, 4: x, 5: x}}
    SYMBOL_PAYS = {
        Symbol.WILD:     {3: 5,    4: 25,  5: 500},
        Symbol.BOOK:     {3: 2,    4: 10,  5: 100},
        Symbol.GOLD_BAR: {3: 1,    4: 5,   5: 50},
        Symbol.DIAMOND:  {3: 0.8,  4: 4,   5: 30},
        Symbol.RUBY:     {3: 0.6,  4: 3,   5: 20},
        Symbol.EMERALD:  {3: 0.5,  4: 2,   5: 15},
        Symbol.CLUB:     {3: 0.3,  4: 1,   5: 8},
        Symbol.SPADE:    {3: 0.2,  4: 0.8, 5: 5},
        Symbol.HEART:    {3: 0.2,  4: 0.8, 5: 5},
    }

    # 20 paylines for a 5-reel, 3-row grid
    # Each entry is [row_reel0, row_reel1, row_reel2, row_reel3, row_reel4]
    # rows: 0 = top, 1 = middle, 2 = bottom
    PAYLINES = {
        1:  [1, 1, 1, 1, 1],  # Middle straight
        2:  [0, 0, 0, 0, 0],  # Top straight
        3:  [2, 2, 2, 2, 2],  # Bottom straight
        4:  [0, 1, 2, 1, 0],  # V-down
        5:  [2, 1, 0, 1, 2],  # V-up (mountain)
        6:  [0, 0, 1, 0, 0],  # Dip middle
        7:  [2, 2, 1, 2, 2],  # Rise middle
        8:  [0, 1, 1, 1, 0],  # Wide dip
        9:  [2, 1, 1, 1, 2],  # Wide rise
        10: [1, 0, 1, 0, 1],  # Zigzag up-down
        11: [1, 2, 1, 2, 1],  # Zigzag down-up
        12: [0, 1, 0, 1, 0],  # Small top zigzag
        13: [2, 1, 2, 1, 2],  # Small bottom zigzag
        14: [0, 0, 1, 2, 2],  # Diagonal step down
        15: [2, 2, 1, 0, 0],  # Diagonal step up
        16: [0, 1, 2, 2, 2],  # Staircase down
        17: [2, 1, 0, 0, 0],  # Staircase up
        18: [1, 1, 0, 1, 1],  # Peak up centre
        19: [1, 1, 2, 1, 1],  # Valley centre
        20: [0, 2, 0, 2, 0],  # Extreme zigzag
    }

    @staticmethod
    def get_payline(payline_num: int) -> list:
        return Paytable.PAYLINES.get(payline_num, [])

    @staticmethod
    def calculate_win(symbol: Symbol, match_count: int, total_bet: float, multiplier: float = 1.0) -> float:
        """
        Calculate win amount.

        Args:
            symbol:      The winning symbol
            match_count: Number of consecutive matches left-to-right (3, 4, or 5)
            total_bet:   Total bet amount (all lines combined)
            multiplier:  Feature multiplier (e.g. 2x in free spins)

        Returns:
            Win amount in currency units
        """
        if match_count < 3 or symbol == Symbol.SCATTER:
            return 0.0
        pays = Paytable.SYMBOL_PAYS.get(symbol, {})
        base = pays.get(match_count, 0)
        return round(base * total_bet * multiplier, 4)

    @staticmethod
    def get_symbol_name(symbol: Symbol) -> str:
        names = {
            Symbol.WILD:     "Wild",
            Symbol.SCATTER:  "Scatter (Book)",
            Symbol.BOOK:     "Book",
            Symbol.GOLD_BAR: "Gold Bar",
            Symbol.DIAMOND:  "Diamond",
            Symbol.RUBY:     "Ruby",
            Symbol.EMERALD:  "Emerald",
            Symbol.CLUB:     "Club",
            Symbol.SPADE:    "Spade",
            Symbol.HEART:    "Heart",
        }
        return names.get(symbol, "Unknown")

    @staticmethod
    def get_symbol_emoji(symbol: Symbol) -> str:
        emojis = {
            Symbol.WILD:     "🃏",
            Symbol.SCATTER:  "📖",
            Symbol.BOOK:     "📚",
            Symbol.GOLD_BAR: "🪙",
            Symbol.DIAMOND:  "💎",
            Symbol.RUBY:     "🔴",
            Symbol.EMERALD:  "💚",
            Symbol.CLUB:     "♣",
            Symbol.SPADE:    "♠",
            Symbol.HEART:    "♥",
        }
        return emojis.get(symbol, "?")
