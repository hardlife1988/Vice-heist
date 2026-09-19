#!/usr/bin/env python3
"""Build Stake-style lookup tables + sample books from the Vice Heist math."""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATH = os.path.join(ROOT, "math")
OUT = os.path.join(MATH, "library", "publish_files")
DIST = os.path.join(ROOT, "dist")

sys.path.insert(0, MATH)

from game_config import GameConfig  # noqa: E402
from reel_engine import ReelEngine  # noqa: E402
from win_evaluator import WinEvaluator  # noqa: E402


def payout_cents(win: float, bet: float) -> int:
    if bet <= 0:
        return 0
    return int(round((win / bet) * 100))


def simulate(n: int, bet: float = 1.0) -> dict:
    config = GameConfig()
    engine = ReelEngine(config)
    evaluator = WinEvaluator(config)
    counts: Counter[int] = Counter()
    total_win = 0.0
    books = []

    for i in range(n):
        grid = engine.spin_reels()
        result = evaluator.evaluate_spin(grid, bet, 1.0)
        win = min(result["total_win"], bet * config.max_win)
        cents = payout_cents(win, bet)
        counts[cents] += 1
        total_win += win
        if i < 250:
            books.append({
                "id": i + 1,
                "payoutMultiplier": cents,
                "events": [{
                    "index": 0,
                    "type": "reveal",
                    "board": [[sym.value for sym in row] for row in grid],
                    "totalWin": round(win, 4),
                    "scatterCount": result["scatter_count"],
                }],
                "criteria": "basegame",
            })

    return {
        "counts": counts,
        "rtp": total_win / (n * bet),
        "n": n,
        "books": books,
        "max_win": config.max_win,
        "name": config.name,
    }


def write_lut(path: str, counts: Counter[int]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "weight", "payoutMultiplier"])
        for i, (mult, weight) in enumerate(sorted(counts.items()), start=1):
            w.writerow([i, weight, mult])


def main() -> None:
    n = int(os.environ.get("VICE_HEIST_SIMS", "20000"))
    print(f"Simulating {n:,} base-game spins…")
    result = simulate(n)
    os.makedirs(OUT, exist_ok=True)
    lut_path = os.path.join(OUT, "lookUpTable_base.csv")
    books_path = os.path.join(OUT, "books_base.jsonl")
    meta_path = os.path.join(OUT, "index.json")

    write_lut(lut_path, result["counts"])
    with open(books_path, "w") as f:
        for book in result["books"]:
            f.write(json.dumps(book) + "\n")

    meta = {
        "gameName": result["name"],
        "mode": "base",
        "spins": result["n"],
        "rtp": round(result["rtp"], 6),
        "maxWin": result["max_win"],
        "lookupTable": "lookUpTable_base.csv",
        "books": "books_base.jsonl",
        "note": "Demo LUT/books from the Flask math engine. Stake ACP still requires official math-sdk books + web-sdk frontend.",
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    os.makedirs(DIST, exist_ok=True)
    static = os.path.join(ROOT, "static")
    for name in ("index.html", "style.css", "game.js"):
        src = os.path.join(static, name)
        dst = os.path.join(DIST, name)
        with open(src, "r", encoding="utf-8") as f:
            data = f.read()
        with open(dst, "w", encoding="utf-8") as f:
            f.write(data)
    with open(os.path.join(DIST, "game_config.json"), "w") as f:
        json.dump({
            "gameName": result["name"],
            "rtp": round(result["rtp"] * 100, 2),
            "maxWin": result["max_win"],
            "paylines": 20,
        }, f, indent=2)

    print(f"RTP (base, {n:,} spins): {result['rtp']*100:.2f}%")
    print(f"Wrote {lut_path}")
    print(f"Wrote {books_path} ({len(result['books'])} sample books)")
    print(f"Copied frontend → {DIST}")


if __name__ == "__main__":
    main()
