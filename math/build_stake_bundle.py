#!/usr/bin/env python3
"""Build Stake Engine math publish files + static frontend bundle."""

from __future__ import annotations

import csv
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATH = os.path.join(ROOT, "math")
OUT = os.path.join(MATH, "library", "publish_files")
DIST = os.path.join(ROOT, "dist")
STATIC = os.path.join(ROOT, "static")

sys.path.insert(0, MATH)

from game_config import GameConfig
from reel_engine import ReelEngine
from win_evaluator import WinEvaluator
from paytable import Paytable
from calibrate_lut import calibrate, weighted_rtp, effective_book_count


BONUS_MIN_EFFECTIVE_RATIO = 0.20


def to_cents(amount: float) -> int:
    return int(round(max(0.0, amount) * 100.0))


def board_from_grid(grid) -> list:
    reels = []

    for reel in range(5):
        reels.append([
            {"name": grid[row][reel].value}
            for row in range(3)
        ])

    return reels


def scatter_positions(grid) -> list:
    positions = []

    for row in range(3):
        for reel in range(5):
            if grid[row][reel].value == "S":
                positions.append({
                    "reel": reel,
                    "row": row,
                })

    return positions


def line_positions(payline_num: int, count: int) -> list:
    line = Paytable.PAYLINES.get(payline_num, [])

    return [
        {
            "reel": reel,
            "row": line[reel],
        }
        for reel in range(min(count, len(line)))
    ]


def eval_to_wins(result: dict) -> list:
    wins = []

    for pw in result["payline_wins"]:
        wins.append({
            "symbol": pw.get("symbol_key") or pw["symbol"],
            "kind": pw["count"],
            "win": to_cents(pw["win"]),
            "positions": line_positions(
                pw["payline"],
                pw["count"],
            ),
            "meta": {
                "payline": pw["payline"],
            },
        })

    if result["scatter_win"] > 0:
        wins.append({
            "symbol": "S",
            "kind": result["scatter_count"],
            "win": to_cents(result["scatter_win"]),
            "positions": [],
            "meta": {
                "scatter": True,
            },
        })

    return wins


class BookBuilder:
    def __init__(self, bet: float = 1.0):
        self.config = GameConfig()
        self.engine = ReelEngine(self.config)
        self.evaluator = WinEvaluator(self.config)
        self.bet = bet

    def _spin(
        self,
        multiplier: float,
        reel_mode: str,
    ):
        grid = self.engine.spin_reels(mode=reel_mode)

        result = self.evaluator.evaluate_spin(
            grid,
            self.bet,
            multiplier,
        )

        win = min(
            result["total_win"],
            self.bet * self.config.max_win,
        )

        result = dict(result)
        result["total_win"] = win

        return grid, result

    def _append_spin_events(
        self,
        events: list,
        grid,
        result,
        game_type: str,
        fs=None,
    ):
        if fs is not None:
            events.append({
                "index": len(events),
                "type": "updateFreeSpin",
                "amount": fs["amount"],
                "total": fs["total"],
            })

        events.append({
            "index": len(events),
            "type": "reveal",
            "board": board_from_grid(grid),
            "paddingPositions": [0, 0, 0, 0, 0],
            "gameType": game_type,
            "anticipation": [0, 0, 0, 0, 0],
        })

        if result["total_win"] > 0 or result["payline_wins"]:
            events.append({
                "index": len(events),
                "type": "winInfo",
                "totalWin": to_cents(result["total_win"]),
                "wins": eval_to_wins(result),
            })

            events.append({
                "index": len(events),
                "type": "setWin",
                "amount": to_cents(result["total_win"]),
                "winLevel": (
                    1
                    if result["total_win"] < self.bet * 5
                    else 2
                ),
            })

    def _run_free_spins(
        self,
        events: list,
        total_fs: int,
        reel_mode: str,
    ) -> float:
        """Run free spins using the requested feature reel distribution."""
        free_win = 0.0

        for i in range(total_fs):
            grid, result = self._spin(
                self.config.free_spins_multiplier,
                reel_mode=reel_mode,
            )

            free_win += result["total_win"]

            self._append_spin_events(
                events,
                grid,
                result,
                "freegame",
                fs={
                    "amount": i + 1,
                    "total": total_fs,
                },
            )

        return free_win

    def build_round(
        self,
        book_id: int,
        mode: str,
    ) -> dict:
        if mode not in ("base", "bonus"):
            raise ValueError(
                f"Unknown book mode: {mode!r}"
            )

        events = []
        total = 0.0
        base_win = 0.0
        free_win = 0.0
        criteria = "basegame"

        if mode == "bonus":
            total_fs = self.config.free_spins_count

            events.append({
                "index": len(events),
                "type": "freeSpinTrigger",
                "totalFs": total_fs,
                "positions": [],
            })

            events.append({
                "index": len(events),
                "type": "enterBonus",
                "reason": "bonusBuy",
            })

            free_win = self._run_free_spins(
                events,
                total_fs,
                reel_mode="bonus_buy",
            )
            total += free_win

            events.append({
                "index": len(events),
                "type": "freeSpinEnd",
                "amount": to_cents(free_win),
                "winLevel": 2,
            })

            criteria = "freegame"

        else:
            # Paid triggering spin remains on the original base reels.
            grid, result = self._spin(
                1.0,
                reel_mode="base",
            )

            total += result["total_win"]
            base_win = result["total_win"]

            self._append_spin_events(
                events,
                grid,
                result,
                "basegame",
            )

            if result["triggers_free_spins"]:
                total_fs = self.config.free_spins_count

                events.append({
                    "index": len(events),
                    "type": "freeSpinTrigger",
                    "totalFs": total_fs,
                    "positions": scatter_positions(grid),
                })

                free_win = self._run_free_spins(
                    events,
                    total_fs,
                    reel_mode="natural_bonus",
                )
                total += free_win

                events.append({
                    "index": len(events),
                    "type": "freeSpinEnd",
                    "amount": to_cents(free_win),
                    "winLevel": 2,
                })

                criteria = "freegame"

        total = min(
            total,
            self.bet * self.config.max_win,
        )

        payout = to_cents(total / self.bet)

        events.append({
            "index": len(events),
            "type": "setTotalWin",
            "amount": to_cents(total),
        })

        events.append({
            "index": len(events),
            "type": "finalWin",
            "amount": to_cents(total),
        })

        return {
            "id": book_id,
            "payoutMultiplier": payout,
            "events": events,
            "criteria": criteria,
            "baseGameWins": round(base_win, 4),
            "freeGameWins": round(free_win, 4),
        }


def write_lut(
    path: str,
    books: list,
    weights: list[int],
) -> None:
    with open(path, "w", newline="") as file:
        writer = csv.writer(file)

        for book, weight in zip(books, weights):
            writer.writerow([
                book["id"],
                weight,
                book["payoutMultiplier"],
            ])


def write_jsonl(path: str, books: list) -> None:
    with open(path, "w", encoding="utf-8") as file:
        for book in books:
            file.write(
                json.dumps(
                    book,
                    separators=(",", ":"),
                )
                + "\n"
            )


def maybe_zstd(src: str) -> str | None:
    dst = src + ".zst"

    try:
        import zstandard as zstd

        compressor = zstd.ZstdCompressor(level=10)

        with open(src, "rb") as inf, open(dst, "wb") as outf:
            compressor.copy_stream(inf, outf)

        return dst

    except Exception as exc:
        print(
            f"zstd skip ({exc}). "
            "Uncompressed jsonl will still be written."
        )
        return None


def copy_frontend() -> None:
    os.makedirs(DIST, exist_ok=True)

    for name in (
        "index.html",
        "style.css",
        "game.js",
    ):
        src = os.path.join(STATIC, name)

        if os.path.isfile(src):
            with open(
                src,
                "r",
                encoding="utf-8",
            ) as file:
                data = file.read()

            with open(
                os.path.join(DIST, name),
                "w",
                encoding="utf-8",
            ) as file:
                file.write(data)


def main() -> None:
    random.seed(
        int(
            os.environ.get(
                "VICE_HEIST_SEED",
                "1988",
            )
        )
    )

    n_base = int(
        os.environ.get(
            "VICE_HEIST_BASE",
            "4000",
        )
    )

    n_bonus = int(
        os.environ.get(
            "VICE_HEIST_BONUS",
            "1200",
        )
    )

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DIST, exist_ok=True)

    builder = BookBuilder(bet=1.0)

    print(
        f"Building {n_base:,} base rounds + "
        f"{n_bonus:,} bonus-buy rounds…"
    )

    base_books = [
        builder.build_round(i, "base")
        for i in range(1, n_base + 1)
    ]

    bonus_books = [
        builder.build_round(i, "bonus")
        for i in range(1, n_bonus + 1)
    ]

    # Raw equal-weight measurements show whether the underlying
    # generated game is healthy before LUT calibration.
    raw_base_weights = [1] * len(base_books)
    raw_bonus_weights = [1] * len(bonus_books)

    raw_base_rtp = weighted_rtp(
        base_books,
        raw_base_weights,
        cost=1.0,
    )

    raw_bonus_rtp = weighted_rtp(
        bonus_books,
        raw_bonus_weights,
        cost=100.0,
    )

    print(
        f"Base raw RTP:           "
        f"{raw_base_rtp * 100:.4f}%"
    )

    print(
        f"Bonus raw RTP:          "
        f"{raw_bonus_rtp * 100:.4f}% (100x cost)"
    )

    # Final deterministic integer LUT calibration.
    base_weights, base_rtp = calibrate(
        base_books,
        cost=1.0,
    )

    bonus_weights, bonus_rtp = calibrate(
        bonus_books,
        cost=100.0,
    )

    fs_rate = (
        sum(
            weight
            for book, weight in zip(
                base_books,
                base_weights,
            )
            if book["criteria"] == "freegame"
        )
        / sum(base_weights)
    )

    base_effective = effective_book_count(
        base_weights
    )

    bonus_effective = effective_book_count(
        bonus_weights
    )

    print(
        f"Base weighted RTP:      "
        f"{base_rtp * 100:.4f}%"
    )

    print(
        f"Bonus weighted RTP:     "
        f"{bonus_rtp * 100:.4f}% (100x cost)"
    )

    print(
        f"Base free-spin hit rate:"
        f" {fs_rate * 100:.2f}% (weighted books)"
    )

    print(
        f"Base effective books:   "
        f"{base_effective:.1f}/{len(base_books)}"
    )

    print(
        f"Bonus effective books:  "
        f"{bonus_effective:.1f}/{len(bonus_books)}"
    )

    minimum_bonus_effective = (
        len(bonus_books)
        * BONUS_MIN_EFFECTIVE_RATIO
    )

    if bonus_effective < minimum_bonus_effective:
        raise RuntimeError(
            "Bonus LUT concentration is too high: "
            f"{bonus_effective:.1f}/{len(bonus_books)} "
            f"effective books; minimum is "
            f"{minimum_bonus_effective:.1f}. "
            "Tune BONUS_REELS before publishing."
        )

    write_lut(
        os.path.join(
            OUT,
            "lookUpTable_base.csv",
        ),
        base_books,
        base_weights,
    )

    write_lut(
        os.path.join(
            OUT,
            "lookUpTable_bonus.csv",
        ),
        bonus_books,
        bonus_weights,
    )

    write_lut(
        os.path.join(
            DIST,
            "lookUpTable_base.csv",
        ),
        base_books,
        base_weights,
    )

    write_lut(
        os.path.join(
            DIST,
            "lookUpTable_bonus.csv",
        ),
        bonus_books,
        bonus_weights,
    )

    base_jsonl = os.path.join(
        OUT,
        "books_base.jsonl",
    )

    bonus_jsonl = os.path.join(
        OUT,
        "books_bonus.jsonl",
    )

    write_jsonl(
        base_jsonl,
        base_books,
    )

    write_jsonl(
        bonus_jsonl,
        bonus_books,
    )

    maybe_zstd(base_jsonl)
    maybe_zstd(bonus_jsonl)

    def slim(books):
        return [
            {
                "id": book["id"],
                "payoutMultiplier": (
                    book["payoutMultiplier"]
                ),
                "events": book["events"],
            }
            for book in books
        ]

    with open(
        os.path.join(
            DIST,
            "books_base.json",
        ),
        "w",
    ) as file:
        json.dump(
            slim(base_books),
            file,
            separators=(",", ":"),
        )

    with open(
        os.path.join(
            DIST,
            "books_bonus.json",
        ),
        "w",
    ) as file:
        json.dump(
            slim(bonus_books),
            file,
            separators=(",", ":"),
        )

    index = {
        "modes": [
            {
                "name": "base",
                "cost": 1.0,
                "events": (
                    "books_base.jsonl.zst"
                    if os.path.isfile(
                        base_jsonl + ".zst"
                    )
                    else "books_base.jsonl"
                ),
                "weights": (
                    "lookUpTable_base.csv"
                ),
            },
            {
                "name": "bonus",
                "cost": 100.0,
                "events": (
                    "books_bonus.jsonl.zst"
                    if os.path.isfile(
                        bonus_jsonl + ".zst"
                    )
                    else "books_bonus.jsonl"
                ),
                "weights": (
                    "lookUpTable_bonus.csv"
                ),
            },
        ]
    }

    with open(
        os.path.join(
            OUT,
            "index.json",
        ),
        "w",
    ) as file:
        json.dump(
            index,
            file,
            indent=2,
        )

    meta = {
        "gameName": "Vice Heist",
        "rtpBase": round(
            base_rtp * 100,
            2,
        ),
        "rtpBonus": round(
            bonus_rtp * 100,
            2,
        ),
        "rawRtpBase": round(
            raw_base_rtp * 100,
            4,
        ),
        "rawRtpBonus": round(
            raw_bonus_rtp * 100,
            4,
        ),
        "maxWin": builder.config.max_win,
        "paylines": 20,
        "baseBooks": n_base,
        "bonusBooks": n_bonus,
        "freeSpinHitRate": round(
            fs_rate,
            4,
        ),
        "baseEffectiveBooks": round(
            base_effective,
            1,
        ),
        "bonusEffectiveBooks": round(
            bonus_effective,
            1,
        ),
        "payoutUnit": "100 = 1.0x bet",
    }

    with open(
        os.path.join(
            DIST,
            "game_config.json",
        ),
        "w",
    ) as file:
        json.dump(
            meta,
            file,
            indent=2,
        )

    with open(
        os.path.join(
            OUT,
            "math_summary.json",
        ),
        "w",
    ) as file:
        json.dump(
            meta,
            file,
            indent=2,
        )

    copy_frontend()

    leftover = os.path.join(
        DIST,
        "main.py",
    )

    if os.path.isfile(leftover):
        os.remove(leftover)

    print(f"Math → {OUT}")
    print(f"Frontend → {DIST}")


if __name__ == "__main__":
    main()
