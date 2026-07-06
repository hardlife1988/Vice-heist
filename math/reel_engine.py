"""
Reel Engine for Vice-heist slot game.
Provably fair spin logic using HMAC-SHA256.

Standard Stake Engine / BC.Game approach:
  hmac_bytes = HMAC-SHA256(key=server_seed, msg=f"{client_seed}:{nonce}")
  Use 2 consecutive bytes per symbol pick (15 picks for 5×3 grid).
  float = int.from_bytes(2 bytes, 'big') / 65536  → [0, 1)
  Apply to cumulative weight distribution to select symbol.
"""

import hmac
import hashlib
import random
from math import ceil
from paytable import Symbol


class ReelWeights:
    """Per-reel weighted symbol distributions for Vice Heist."""

    REEL_1 = {
        Symbol.WILD:     15,
        Symbol.SCATTER:  3,
        Symbol.BOOK:     8,
        Symbol.GOLD_BAR: 12,
        Symbol.DIAMOND:  15,
        Symbol.RUBY:     18,
        Symbol.EMERALD:  12,
        Symbol.CLUB:     10,
        Symbol.SPADE:    10,
        Symbol.HEART:    10,
    }

    REEL_2 = {
        Symbol.WILD:     12,
        Symbol.SCATTER:  3,
        Symbol.BOOK:     10,
        Symbol.GOLD_BAR: 15,
        Symbol.DIAMOND:  14,
        Symbol.RUBY:     16,
        Symbol.EMERALD:  14,
        Symbol.CLUB:     10,
        Symbol.SPADE:    12,
        Symbol.HEART:    11,
    }

    REEL_3 = {
        Symbol.WILD:     20,  # Higher wild frequency on middle reel
        Symbol.SCATTER:  4,
        Symbol.BOOK:     12,
        Symbol.GOLD_BAR: 12,
        Symbol.DIAMOND:  14,
        Symbol.RUBY:     14,
        Symbol.EMERALD:  12,
        Symbol.CLUB:     10,
        Symbol.SPADE:    10,
        Symbol.HEART:    10,
    }

    REEL_4 = {
        Symbol.WILD:     12,
        Symbol.SCATTER:  3,
        Symbol.BOOK:     10,
        Symbol.GOLD_BAR: 15,
        Symbol.DIAMOND:  14,
        Symbol.RUBY:     16,
        Symbol.EMERALD:  14,
        Symbol.CLUB:     10,
        Symbol.SPADE:    12,
        Symbol.HEART:    11,
    }

    REEL_5 = {
        Symbol.WILD:     15,
        Symbol.SCATTER:  3,
        Symbol.BOOK:     8,
        Symbol.GOLD_BAR: 12,
        Symbol.DIAMOND:  15,
        Symbol.RUBY:     18,
        Symbol.EMERALD:  12,
        Symbol.CLUB:     10,
        Symbol.SPADE:    10,
        Symbol.HEART:    10,
    }

    ALL_REELS = [REEL_1, REEL_2, REEL_3, REEL_4, REEL_5]


def _build_cumulative(weights: dict):
    """Return (symbols_list, cumulative_list, total)."""
    symbols = list(weights.keys())
    cumulative = []
    running = 0
    for s in symbols:
        running += weights[s]
        cumulative.append(running)
    return symbols, cumulative, running


def _pick_from_cumulative(rand_int: int, symbols, cumulative, total: int) -> Symbol:
    """Select a symbol using a raw integer in [0, total)."""
    val = rand_int % total
    for sym, cum in zip(symbols, cumulative):
        if val < cum:
            return sym
    return symbols[-1]  # fallback (should never reach here)


def spin_provably_fair(server_seed: str, client_seed: str, nonce: int,
                       reels: int = 5, rows: int = 3) -> list:
    """
    Spin all reels using HMAC-SHA256 provably fair RNG.

    Returns a 3×5 grid: result_grid[row][reel] = Symbol
    """
    # Generate HMAC-SHA256 hash
    message = f"{client_seed}:{nonce}".encode()
    hash_bytes = hmac.new(server_seed.encode(), message, hashlib.sha256).digest()
    # 32 bytes available; 5 reels × 3 rows = 15 picks × 2 bytes = 30 bytes — fits.

    # Pre-compute cumulative distributions
    cum_data = [_build_cumulative(ReelWeights.ALL_REELS[r]) for r in range(reels)]

    # Pick symbols reel by reel
    reel_columns = []
    byte_idx = 0
    for reel_num in range(reels):
        symbols, cumulative, total = cum_data[reel_num]
        col = []
        for _ in range(rows):
            # Use 2 bytes → 16-bit integer
            raw = (hash_bytes[byte_idx] << 8) | hash_bytes[byte_idx + 1]
            byte_idx += 2
            col.append(_pick_from_cumulative(raw, symbols, cumulative, total))
        reel_columns.append(col)

    # Transpose to row-major: result_grid[row][reel]
    grid = []
    for row in range(rows):
        grid.append([reel_columns[reel][row] for reel in range(reels)])
    return grid


class ReelEngine:
    """
    Manages reel spins.

    Prefer spin_provably_fair() directly for Stake Engine use.
    This class wraps it for backwards compatibility with the CLI tools.
    """

    def __init__(self, config):
        self.config = config
        self.reels = config.reels
        self.rows = config.rows

    def spin_reels(self, server_seed: str = None, client_seed: str = None, nonce: int = 0) -> list:
        """
        Spin all reels.

        If server_seed and client_seed are provided, uses provably fair RNG.
        Otherwise falls back to Python's random (for local testing only).
        """
        if server_seed and client_seed:
            return spin_provably_fair(server_seed, client_seed, nonce, self.reels, self.rows)
        # Fallback: insecure random (local CLI testing only)
        reel_columns = []
        for reel_num in range(self.reels):
            weights_dict = ReelWeights.ALL_REELS[reel_num]
            symbols, cumulative, total = _build_cumulative(weights_dict)
            col = [_pick_from_cumulative(random.randint(0, total - 1), symbols, cumulative, total)
                   for _ in range(self.rows)]
            reel_columns.append(col)
        grid = []
        for row in range(self.rows):
            grid.append([reel_columns[reel][row] for reel in range(self.reels)])
        return grid

    def get_reel_result_display(self, reel_grid) -> str:
        display = ""
        for row in reel_grid:
            display += " | ".join([s.value for s in row]) + "\n"
        return display
