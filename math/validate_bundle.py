"""Validate a Vice Heist bundle without changing or regenerating it.

Usage:
    python math/validate_bundle.py

Checks both lookup tables and their corresponding frontend book JSON files.
Requires the repository's dist/ bundle to have been generated already.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
TARGET_RTP = 0.96
RTP_TOLERANCE = 0.005  # half a percentage point


def read_mode(mode: str, cost: float) -> dict:
    books_path = DIST / f"books_{mode}.json"
    lut_path = DIST / f"lookUpTable_{mode}.csv"

    with books_path.open(encoding="utf-8") as file:
        books = json.load(file)
    if not isinstance(books, list) or not books:
        raise ValueError(f"{mode}: books must be a nonempty JSON array")

    by_id = {}
    for book in books:
        book_id = book["id"]
        if not isinstance(book_id, int) or book_id <= 0 or book_id in by_id:
            raise ValueError(f"{mode}: invalid/duplicate book ID {book_id}")
        payout = book["payoutMultiplier"]
        if not isinstance(payout, int) or payout < 0:
            raise ValueError(f"{mode}: invalid payout for book {book_id}")
        events = book["events"]
        if not isinstance(events, list) or not events:
            raise ValueError(f"{mode}: empty events in book {book_id}")
        finals = [e for e in events if e.get("type") == "finalWin"]
        totals = [e for e in events if e.get("type") == "setTotalWin"]
        if len(finals) != 1 or len(totals) != 1:
            raise ValueError(f"{mode}: missing/duplicate final events: {book_id}")
        if finals[0]["amount"] != payout or totals[0]["amount"] != payout:
            raise ValueError(f"{mode}: final payout mismatch: {book_id}")
        if payout > 1_000_000:
            raise ValueError(f"{mode}: payout exceeds 10,000x: {book_id}")
        by_id[book_id] = book

    weighted_payout = 0
    total_weight = 0
    seen = set()
    with lut_path.open(newline="", encoding="utf-8") as file:
        for row in csv.reader(file):
            if len(row) != 3:
                raise ValueError(f"{mode}: LUT must have three columns")
            book_id, weight, payout = map(int, row)
            if book_id in seen or book_id not in by_id:
                raise ValueError(f"{mode}: missing/duplicate LUT ID {book_id}")
            if weight <= 0 or payout != by_id[book_id]["payoutMultiplier"]:
                raise ValueError(f"{mode}: invalid weight/payout: {book_id}")
            seen.add(book_id)
            total_weight += weight
            weighted_payout += weight * payout

    if seen != set(by_id):
        raise ValueError(f"{mode}: some books have no LUT row")
    # payoutMultiplier 100 means 1x ordinary bet.
    rtp = weighted_payout / (total_weight * 100 * cost)
    return {"mode": mode, "books": len(books), "rtp": rtp,
            "target_met": math.isclose(rtp, TARGET_RTP,
                                       abs_tol=RTP_TOLERANCE)}


def main() -> None:
    results = [read_mode("base", 1), read_mode("bonus", 100)]
    for result in results:
        print(f"{result['mode']}: {result['books']} books; "
              f"RTP {result['rtp']:.4%}; "
              f"96% target: {'PASS' if result['target_met'] else 'FAIL'}")
    if not all(result["target_met"] for result in results):
        raise SystemExit(
            "Validation failed: keep the existing bundle unpublished. "
            "Calibrate the generated outcomes and lookup weights first."
        )
    print("PASS: Both modes meet the configured RTP tolerance.")


if __name__ == "__main__":
    main()
