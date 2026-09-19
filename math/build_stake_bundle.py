#!/usr/bin/env python3
"""Build Stake Engine math publish files + a static frontend bundle.

Outputs
-------
math/library/publish_files/
  index.json
  lookUpTable_base.csv
  lookUpTable_bonus.csv
  books_base.jsonl[.zst]
  books_bonus.jsonl[.zst]
dist/
  index.html, style.css, game.js
  books_base.json, books_bonus.json
  lookUpTable_base.csv, lookUpTable_bonus.csv
  game_config.json
"""
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

from game_config import GameConfig  # noqa: E402
from reel_engine import ReelEngine  # noqa: E402
from win_evaluator import WinEvaluator  # noqa: E402
from paytable import Paytable  # noqa: E402


def to_cents(amount: float) -> int:
    return int(round(max(0.0, amount) * 100.0))


def board_from_grid(grid) -> list:
    """Row-major Symbol grid → Stake reel-major [{name}] board."""
    reels = []
    for reel in range(5):
        reels.append([{"name": grid[row][reel].value} for row in range(3)])
    return reels


def scatter_positions(grid) -> list:
    positions = []
    for row in range(3):
        for reel in range(5):
            if grid[row][reel].value == "S":
                positions.append({"reel": reel, "row": row})
    return positions


def line_positions(payline_num: int, count: int) -> list:
    line = Paytable.PAYLINES.get(payline_num, [])
    return [{"reel": reel, "row": line[reel]} for reel in range(min(count, len(line)))]


def eval_to_wins(result: dict) -> list:
    wins = []
    for pw in result["payline_wins"]:
        wins.append({
            "symbol": pw.get("symbol_key") or pw["symbol"],
            "kind": pw["count"],
            "win": to_cents(pw["win"]),
            "positions": line_positions(pw["payline"], pw["count"]),
            "meta": {"payline": pw["payline"]},
        })
    if result["scatter_win"] > 0:
        wins.append({
            "symbol": "S",
            "kind": result["scatter_count"],
            "win": to_cents(result["scatter_win"]),
            "positions": [],
            "meta": {"scatter": True},
        })
    return wins


class BookBuilder:
    def __init__(self, bet: float = 1.0):
        self.config = GameConfig()
        self.engine = ReelEngine(self.config)
        self.evaluator = WinEvaluator(self.config)
        self.bet = bet

    def _spin(self, multiplier: float):
        grid = self.engine.spin_reels()
        result = self.evaluator.evaluate_spin(grid, self.bet, multiplier)
        win = min(result["total_win"], self.bet * self.config.max_win)
        result = dict(result)
        result["total_win"] = win
        return grid, result

    def _append_spin_events(self, events: list, grid, result, game_type: str, fs=None):
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
                "winLevel": 1 if result["total_win"] < self.bet * 5 else 2,
            })

    def build_round(self, book_id: int, mode: str) -> dict:
        events = []
        total = 0.0
        base_win = 0.0
        free_win = 0.0
        criteria = "basegame"

        if mode == "bonus":
            tot_fs = self.config.free_spins_count
            events.append({
                "index": 0,
                "type": "freeSpinTrigger",
                "totalFs": tot_fs,
                "positions": [],
            })
            events.append({
                "index": 1,
                "type": "enterBonus",
                "reason": "bonusBuy",
            })
            for i in range(tot_fs):
                grid, result = self._spin(self.config.free_spins_multiplier)
                total += result["total_win"]
                free_win += result["total_win"]
                self._append_spin_events(
                    events, grid, result, "freegame",
                    fs={"amount": i + 1, "total": tot_fs},
                )
            events.append({
                "index": len(events),
                "type": "freeSpinEnd",
                "amount": to_cents(free_win),
                "winLevel": 2,
            })
            criteria = "freegame"
        else:
            grid, result = self._spin(1.0)
            total += result["total_win"]
            base_win = result["total_win"]
            self._append_spin_events(events, grid, result, "basegame")
            if result["triggers_free_spins"]:
                tot_fs = self.config.free_spins_count
                events.append({
                    "index": len(events),
                    "type": "freeSpinTrigger",
                    "totalFs": tot_fs,
                    "positions": scatter_positions(grid),
                })
                for i in range(tot_fs):
                    g2, r2 = self._spin(self.config.free_spins_multiplier)
                    total += r2["total_win"]
                    free_win += r2["total_win"]
                    self._append_spin_events(
                        events, g2, r2, "freegame",
                        fs={"amount": i + 1, "total": tot_fs},
                    )
                events.append({
                    "index": len(events),
                    "type": "freeSpinEnd",
                    "amount": to_cents(free_win),
                    "winLevel": 2,
                })
                criteria = "freegame"

        total = min(total, self.bet * self.config.max_win)
        payout = to_cents(total / self.bet)  # 100 = 1.0x
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


def write_lut(path: str, books: list) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        for b in books:
            w.writerow([b["id"], 1, b["payoutMultiplier"]])


def write_jsonl(path: str, books: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for b in books:
            f.write(json.dumps(b, separators=(",", ":")) + "\n")


def maybe_zstd(src: str) -> str | None:
    dst = src + ".zst"
    try:
        import zstandard as zstd
        cctx = zstd.ZstdCompressor(level=10)
        with open(src, "rb") as inf, open(dst, "wb") as outf:
            cctx.copy_stream(inf, outf)
        return dst
    except Exception as exc:
        print(f"zstd skip ({exc}). Uncompressed jsonl will still be written.")
        return None


def copy_frontend() -> None:
    os.makedirs(DIST, exist_ok=True)
    for name in ("index.html", "style.css", "game.js"):
        src = os.path.join(STATIC, name)
        if os.path.isfile(src):
            with open(src, "r", encoding="utf-8") as f:
                data = f.read()
            with open(os.path.join(DIST, name), "w", encoding="utf-8") as f:
                f.write(data)


def main() -> None:
    random.seed(int(os.environ.get("VICE_HEIST_SEED", "1988")))
    n_base = int(os.environ.get("VICE_HEIST_BASE", "4000"))
    n_bonus = int(os.environ.get("VICE_HEIST_BONUS", "1200"))
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DIST, exist_ok=True)

    builder = BookBuilder(bet=1.0)
    print(f"Building {n_base:,} base rounds + {n_bonus:,} bonus-buy rounds…")
    base_books = [builder.build_round(i, "base") for i in range(1, n_base + 1)]
    bonus_books = [builder.build_round(i, "bonus") for i in range(1, n_bonus + 1)]

    def rtp(books, cost):
        if not books:
            return 0.0
        return sum(b["payoutMultiplier"] for b in books) / (len(books) * cost * 100.0)

    base_rtp = rtp(base_books, 1.0)
    bonus_rtp = rtp(bonus_books, 100.0)
    fs_rate = sum(1 for b in base_books if b["criteria"] == "freegame") / len(base_books)

    print(f"Base RTP (equal weights): {base_rtp*100:.2f}%")
    print(f"Bonus RTP vs 100x cost:   {bonus_rtp*100:.2f}%")
    print(f"Base free-spin hit rate:  {fs_rate*100:.2f}%")

    write_lut(os.path.join(OUT, "lookUpTable_base.csv"), base_books)
    write_lut(os.path.join(OUT, "lookUpTable_bonus.csv"), bonus_books)
    write_lut(os.path.join(DIST, "lookUpTable_base.csv"), base_books)
    write_lut(os.path.join(DIST, "lookUpTable_bonus.csv"), bonus_books)

    base_jsonl = os.path.join(OUT, "books_base.jsonl")
    bonus_jsonl = os.path.join(OUT, "books_bonus.jsonl")
    write_jsonl(base_jsonl, base_books)
    write_jsonl(bonus_jsonl, bonus_books)
    maybe_zstd(base_jsonl)
    maybe_zstd(bonus_jsonl)

    # Compact frontend copies (events only + payout)
    def slim(books):
        return [{"id": b["id"], "payoutMultiplier": b["payoutMultiplier"], "events": b["events"]} for b in books]

    with open(os.path.join(DIST, "books_base.json"), "w") as f:
        json.dump(slim(base_books), f, separators=(",", ":"))
    with open(os.path.join(DIST, "books_bonus.json"), "w") as f:
        json.dump(slim(bonus_books), f, separators=(",", ":"))

    index = {
        "modes": [
            {
                "name": "base",
                "cost": 1.0,
                "events": "books_base.jsonl.zst" if os.path.isfile(base_jsonl + ".zst") else "books_base.jsonl",
                "weights": "lookUpTable_base.csv",
            },
            {
                "name": "bonus",
                "cost": 100.0,
                "events": "books_bonus.jsonl.zst" if os.path.isfile(bonus_jsonl + ".zst") else "books_bonus.jsonl",
                "weights": "lookUpTable_bonus.csv",
            },
        ]
    }
    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump(index, f, indent=2)

    meta = {
        "gameName": "Vice Heist",
        "rtpBase": round(base_rtp * 100, 2),
        "rtpBonus": round(bonus_rtp * 100, 2),
        "maxWin": builder.config.max_win,
        "paylines": 20,
        "baseBooks": n_base,
        "bonusBooks": n_bonus,
        "freeSpinHitRate": round(fs_rate, 4),
        "payoutUnit": "100 = 1.0x bet",
    }
    with open(os.path.join(DIST, "game_config.json"), "w") as f:
        json.dump(meta, f, indent=2)
    with open(os.path.join(OUT, "math_summary.json"), "w") as f:
        json.dump(meta, f, indent=2)

    copy_frontend()
    leftover = os.path.join(DIST, "main.py")
    if os.path.isfile(leftover):
        os.remove(leftover)
    print(f"Math → {OUT}")
    print(f"Frontend → {DIST}")


if __name__ == "__main__":
    main()
