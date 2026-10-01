"""
Reel engine for Vice Heist.

Provides separate base-game and bonus/free-spin symbol distributions.

Provably-fair RNG:
    HMAC-SHA256(key=server_seed, message=f"{client_seed}:{nonce}:{block}")

Random values are mapped to weighted symbols using rejection sampling rather
than modulo reduction, avoiding modulo bias.
"""

from __future__ import annotations

import hashlib
import hmac
import random

from paytable import Symbol


class ReelWeights:
    """Per-reel weighted symbol distributions."""

    # Keep the already-working base-game distribution unchanged.
    BASE_REELS = [
        {
            Symbol.WILD: 15,
            Symbol.SCATTER: 3,
            Symbol.BOOK: 8,
            Symbol.GOLD_BAR: 12,
            Symbol.DIAMOND: 15,
            Symbol.RUBY: 18,
            Symbol.EMERALD: 12,
            Symbol.CLUB: 10,
            Symbol.SPADE: 10,
            Symbol.HEART: 10,
        },
        {
            Symbol.WILD: 12,
            Symbol.SCATTER: 3,
            Symbol.BOOK: 10,
            Symbol.GOLD_BAR: 15,
            Symbol.DIAMOND: 14,
            Symbol.RUBY: 16,
            Symbol.EMERALD: 14,
            Symbol.CLUB: 10,
            Symbol.SPADE: 12,
            Symbol.HEART: 11,
        },
        {
            Symbol.WILD: 20,
            Symbol.SCATTER: 4,
            Symbol.BOOK: 12,
            Symbol.GOLD_BAR: 12,
            Symbol.DIAMOND: 14,
            Symbol.RUBY: 14,
            Symbol.EMERALD: 12,
            Symbol.CLUB: 10,
            Symbol.SPADE: 10,
            Symbol.HEART: 10,
        },
        {
            Symbol.WILD: 12,
            Symbol.SCATTER: 3,
            Symbol.BOOK: 10,
            Symbol.GOLD_BAR: 15,
            Symbol.DIAMOND: 14,
            Symbol.RUBY: 16,
            Symbol.EMERALD: 14,
            Symbol.CLUB: 10,
            Symbol.SPADE: 12,
            Symbol.HEART: 11,
        },
        {
            Symbol.WILD: 15,
            Symbol.SCATTER: 3,
            Symbol.BOOK: 8,
            Symbol.GOLD_BAR: 12,
            Symbol.DIAMOND: 15,
            Symbol.RUBY: 18,
            Symbol.EMERALD: 12,
            Symbol.CLUB: 10,
            Symbol.SPADE: 10,
            Symbol.HEART: 10,
        },
    ]

    # Bonus/free-spin distribution.
    #
    # The increased Wild frequency is the starting calibration for the
    # 10-spin, 2x-multiplier feature. The generated bundle remains the
    # authority for measured RTP.
    BONUS_REELS = [
        {
            Symbol.WILD: 31,
            Symbol.SCATTER: 3,
            Symbol.BOOK: 8,
            Symbol.GOLD_BAR: 12,
            Symbol.DIAMOND: 15,
            Symbol.RUBY: 18,
            Symbol.EMERALD: 12,
            Symbol.CLUB: 10,
            Symbol.SPADE: 10,
            Symbol.HEART: 10,
        },
        {
            Symbol.WILD: 32,
            Symbol.SCATTER: 3,
            Symbol.BOOK: 10,
            Symbol.GOLD_BAR: 15,
            Symbol.DIAMOND: 14,
            Symbol.RUBY: 16,
            Symbol.EMERALD: 14,
            Symbol.CLUB: 10,
            Symbol.SPADE: 12,
            Symbol.HEART: 11,
        },
        {
            Symbol.WILD: 41,
            Symbol.SCATTER: 4,
            Symbol.BOOK: 12,
            Symbol.GOLD_BAR: 12,
            Symbol.DIAMOND: 14,
            Symbol.RUBY: 14,
            Symbol.EMERALD: 12,
            Symbol.CLUB: 10,
            Symbol.SPADE: 10,
            Symbol.HEART: 10,
        },
        {
            Symbol.WILD: 32,
            Symbol.SCATTER: 3,
            Symbol.BOOK: 10,
            Symbol.GOLD_BAR: 15,
            Symbol.DIAMOND: 14,
            Symbol.RUBY: 16,
            Symbol.EMERALD: 14,
            Symbol.CLUB: 10,
            Symbol.SPADE: 12,
            Symbol.HEART: 11,
        },
        {
            Symbol.WILD: 31,
            Symbol.SCATTER: 3,
            Symbol.BOOK: 8,
            Symbol.GOLD_BAR: 12,
            Symbol.DIAMOND: 15,
            Symbol.RUBY: 18,
            Symbol.EMERALD: 12,
            Symbol.CLUB: 10,
            Symbol.SPADE: 10,
            Symbol.HEART: 10,
        },
    ]

    # Backwards compatibility for anything still referencing ALL_REELS.
    ALL_REELS = BASE_REELS

    @classmethod
    def for_mode(cls, mode: str):
        if mode == "base":
            return cls.BASE_REELS
        if mode == "bonus":
            return cls.BONUS_REELS
        raise ValueError(f"Unknown reel mode: {mode!r}")


def _build_cumulative(weights: dict):
    """Return symbols, cumulative integer weights and total weight."""
    symbols = list(weights.keys())
    cumulative = []
    running = 0

    for symbol in symbols:
        weight = weights[symbol]

        if not isinstance(weight, int) or weight <= 0:
            raise ValueError("Reel weights must be positive integers")

        running += weight
        cumulative.append(running)

    return symbols, cumulative, running


def _pick_from_index(value: int, symbols, cumulative) -> Symbol:
    """Select a symbol from an already unbiased integer index."""
    for symbol, upper_bound in zip(symbols, cumulative):
        if value < upper_bound:
            return symbol

    raise RuntimeError("Weighted symbol selection exceeded cumulative range")


def _random_weight_index(rng, total: int) -> int:
    """
    Generate an unbiased integer in [0, total).

    rng() must return an unsigned 32-bit integer.

    Rejection sampling removes the bias produced by simply doing
    random_value % total when 2**32 is not divisible by total.
    """
    if total <= 0:
        raise ValueError("Total reel weight must be positive")

    range_size = 1 << 32
    limit = range_size - (range_size % total)

    while True:
        value = rng()
        if value < limit:
            return value % total


class _HmacWordStream:
    """Deterministic stream of unsigned 32-bit values."""

    def __init__(self, server_seed: str, client_seed: str, nonce: int):
        if not server_seed:
            raise ValueError("server_seed must not be empty")
        if not client_seed:
            raise ValueError("client_seed must not be empty")
        if nonce < 0:
            raise ValueError("nonce must be non-negative")

        self.server_seed = server_seed.encode("utf-8")
        self.client_seed = client_seed
        self.nonce = nonce

        self.block = 0
        self.buffer = b""
        self.offset = 0

    def _refill(self):
        message = (
            f"{self.client_seed}:{self.nonce}:{self.block}"
        ).encode("utf-8")

        self.buffer = hmac.new(
            self.server_seed,
            message,
            hashlib.sha256,
        ).digest()

        self.offset = 0
        self.block += 1

    def next_u32(self) -> int:
        if self.offset + 4 > len(self.buffer):
            self._refill()

        value = int.from_bytes(
            self.buffer[self.offset:self.offset + 4],
            "big",
        )
        self.offset += 4
        return value


def spin_provably_fair(
    server_seed: str,
    client_seed: str,
    nonce: int,
    reels: int = 5,
    rows: int = 3,
    mode: str = "base",
) -> list:
    """
    Generate a deterministic reel grid using HMAC-SHA256.

    Returns:
        3x5 row-major Symbol grid for the standard Vice Heist layout.
    """
    reel_weights = ReelWeights.for_mode(mode)

    if reels != len(reel_weights):
        raise ValueError(
            f"Vice Heist requires {len(reel_weights)} reels; got {reels}"
        )

    if rows <= 0:
        raise ValueError("rows must be positive")

    stream = _HmacWordStream(server_seed, client_seed, nonce)

    reel_columns = []

    for reel_num in range(reels):
        symbols, cumulative, total = _build_cumulative(
            reel_weights[reel_num]
        )

        column = []

        for _ in range(rows):
            index = _random_weight_index(
                stream.next_u32,
                total,
            )
            column.append(
                _pick_from_index(index, symbols, cumulative)
            )

        reel_columns.append(column)

    return [
        [
            reel_columns[reel][row]
            for reel in range(reels)
        ]
        for row in range(rows)
    ]


class ReelEngine:
    """Generate base-game and bonus/free-spin reel grids."""

    def __init__(self, config):
        self.config = config
        self.reels = config.reels
        self.rows = config.rows

    def spin_reels(
        self,
        server_seed: str | None = None,
        client_seed: str | None = None,
        nonce: int = 0,
        mode: str = "base",
    ) -> list:
        """
        Spin all reels.

        Supplied seeds use deterministic HMAC-SHA256 generation.
        Without seeds, Python's PRNG is used only for offline book generation
        and local testing.
        """
        reel_weights = ReelWeights.for_mode(mode)

        if server_seed is not None or client_seed is not None:
            if not server_seed or not client_seed:
                raise ValueError(
                    "Both server_seed and client_seed are required"
                )

            return spin_provably_fair(
                server_seed,
                client_seed,
                nonce,
                self.reels,
                self.rows,
                mode,
            )

        reel_columns = []

        for reel_num in range(self.reels):
            symbols, cumulative, total = _build_cumulative(
                reel_weights[reel_num]
            )

            column = []

            for _ in range(self.rows):
                index = random.randrange(total)
                column.append(
                    _pick_from_index(index, symbols, cumulative)
                )

            reel_columns.append(column)

        return [
            [
                reel_columns[reel][row]
                for reel in range(self.reels)
            ]
            for row in range(self.rows)
        ]

    def get_reel_result_display(self, reel_grid) -> str:
        return "".join(
            " | ".join(symbol.value for symbol in row) + "\n"
            for row in reel_grid
        )
