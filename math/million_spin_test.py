#!/usr/bin/env python3
"""
VICE HEIST million-round math stress test.

Tests two separate layers:

1. RAW ENGINE
   Directly generates rounds from BookBuilder without LUT calibration.

2. PUBLISHED LUT
   Samples the generated books using their published integer weights.

No game files or math parameters are modified by this script.
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
import statistics
import sys
import time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATH = os.path.join(ROOT, "math")
OUT = os.path.join(MATH, "library", "publish_files")

sys.path.insert(0, MATH)

from build_stake_bundle import BookBuilder


ROUNDS = int(os.environ.get("VICE_HEIST_STRESS_ROUNDS", "1000000"))
SEED = int(os.environ.get("VICE_HEIST_STRESS_SEED", "1988"))

MAX_WIN = 10_000.0
BONUS_COST = 100.0

THRESHOLDS = (
    1,
    10,
    50,
    100,
    500,
    1_000,
    5_000,
    10_000,
)


class Stats:
    def __init__(self, cost: float):
        self.cost = cost
        self.count = 0
        self.total_payout = 0.0
        self.total_squared = 0.0
        self.hits = 0
        self.zeroes = 0
        self.max_payout = 0.0
        self.max_win_violations = 0
        self.free_spin_triggers = 0
        self.thresholds = Counter()

        # Exact median over one million floats is still reasonable
        # in Codespaces memory.
        self.payouts = []

        self.bonus_losses = 0
        self.bonus_breakeven = 0
        self.bonus_profit = 0

    def add(
        self,
        payout: float,
        free_spin_trigger: bool = False,
    ):
        payout = float(payout)

        self.count += 1
        self.total_payout += payout
        self.total_squared += payout * payout
        self.payouts.append(payout)

        if payout > 0:
            self.hits += 1
        else:
            self.zeroes += 1

        if payout > self.max_payout:
            self.max_payout = payout

        if payout > MAX_WIN + 1e-9:
            self.max_win_violations += 1

        if free_spin_trigger:
            self.free_spin_triggers += 1

        for threshold in THRESHOLDS:
            if payout >= threshold:
                self.thresholds[threshold] += 1

        if self.cost == BONUS_COST:
            if payout < BONUS_COST:
                self.bonus_losses += 1
            elif math.isclose(
                payout,
                BONUS_COST,
                rel_tol=0.0,
                abs_tol=0.005,
            ):
                self.bonus_breakeven += 1
            else:
                self.bonus_profit += 1

    def report(self, title: str):
        if not self.count:
            return

        mean_payout = self.total_payout / self.count
        rtp = mean_payout / self.cost

        variance = max(
            0.0,
            (self.total_squared / self.count)
            - (mean_payout * mean_payout),
        )

        sd = math.sqrt(variance)

        # Standard error expressed in RTP units.
        rtp_se = (sd / math.sqrt(self.count)) / self.cost
        ci_low = rtp - 1.96 * rtp_se
        ci_high = rtp + 1.96 * rtp_se

        median = statistics.median(self.payouts)

        print()
        print("=" * 72)
        print(title)
        print("=" * 72)

        print(f"Rounds:                    {self.count:,}")
        print(f"Cost per round:            {self.cost:.2f}x")
        print(f"Total wagered:             {self.count * self.cost:,.2f}x")
        print(f"Total returned:            {self.total_payout:,.2f}x")
        print(f"RTP:                       {rtp * 100:.6f}%")
        print(f"RTP standard error:        {rtp_se * 100:.6f}%")
        print(
            "Approx. 95% RTP interval: "
            f"{ci_low * 100:.6f}% - {ci_high * 100:.6f}%"
        )

        print(
            f"Hit frequency:             "
            f"{self.hits / self.count * 100:.6f}%"
        )

        print(
            f"Zero-win frequency:        "
            f"{self.zeroes / self.count * 100:.6f}%"
        )

        print(f"Average payout:            {mean_payout:.6f}x")
        print(f"Median payout:             {median:.6f}x")
        print(f"Maximum observed payout:   {self.max_payout:.6f}x")

        print(
            f"Max-win violations:        "
            f"{self.max_win_violations:,}"
        )

        if self.free_spin_triggers:
            rate = self.free_spin_triggers / self.count

            print(
                f"Free-spin triggers:        "
                f"{self.free_spin_triggers:,}"
            )

            print(
                f"Free-spin trigger rate:    "
                f"{rate * 100:.6f}%"
            )

            print(
                f"Approx. trigger frequency: "
                f"1 in {1 / rate:,.2f}"
            )

        print()
        print("PAYOUT THRESHOLDS")

        for threshold in THRESHOLDS:
            hits = self.thresholds[threshold]
            rate = hits / self.count

            frequency = (
                f"1 in {1 / rate:,.2f}"
                if rate > 0
                else "never observed"
            )

            print(
                f">= {threshold:>6,}x: "
                f"{hits:>10,}  "
                f"{rate * 100:>10.6f}%  "
                f"{frequency}"
            )

        if self.cost == BONUS_COST:
            print()
            print("BONUS BUY OUTCOMES")

            print(
                f"Loss (<100x):              "
                f"{self.bonus_losses:,} "
                f"({self.bonus_losses / self.count * 100:.6f}%)"
            )

            print(
                f"Breakeven (=100x):         "
                f"{self.bonus_breakeven:,} "
                f"({self.bonus_breakeven / self.count * 100:.6f}%)"
            )

            print(
                f"Profit (>100x):            "
                f"{self.bonus_profit:,} "
                f"({self.bonus_profit / self.count * 100:.6f}%)"
            )


def load_lut(mode: str):
    path = os.path.join(
        OUT,
        f"lookUpTable_{mode}.csv",
    )

    rows = []

    with open(path, newline="") as file:
        reader = csv.reader(file)

        for row in reader:
            if not row:
                continue

            book_id = int(row[0])
            weight = int(row[1])
            payout = int(row[2]) / 100.0

            rows.append(
                (book_id, weight, payout)
            )

    if not rows:
        raise RuntimeError(
            f"No LUT rows found in {path}"
        )

    return rows


def load_books(mode: str):
    path = os.path.join(
        OUT,
        f"books_{mode}.jsonl",
    )

    books = {}

    with open(path, encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            book = json.loads(line)
            books[int(book["id"])] = book

    if not books:
        raise RuntimeError(
            f"No books found in {path}"
        )

    return books


def published_test(
    mode: str,
    rounds: int,
    rng: random.Random,
):
    cost = 1.0 if mode == "base" else BONUS_COST
    stats = Stats(cost)

    lut = load_lut(mode)
    books = load_books(mode)

    ids = [row[0] for row in lut]
    weights = [row[1] for row in lut]

    # Payout comes directly from the published LUT.
    payout_by_id = {
        row[0]: row[2]
        for row in lut
    }

    # criteria exists in JSONL and tells us whether a base
    # book entered the free game.
    criteria_by_id = {
        book_id: book.get("criteria", "")
        for book_id, book in books.items()
    }

    print(
        f"\nSampling {rounds:,} published "
        f"{mode.upper()} rounds..."
    )

    start = time.time()

    # Chunk sampling keeps memory overhead under control.
    chunk_size = 100_000
    completed = 0

    while completed < rounds:
        n = min(
            chunk_size,
            rounds - completed,
        )

        selections = rng.choices(
            ids,
            weights=weights,
            k=n,
        )

        for book_id in selections:
            stats.add(
                payout_by_id[book_id],
                free_spin_trigger=(
                    mode == "base"
                    and criteria_by_id.get(book_id)
                    == "freegame"
                ),
            )

        completed += n

        if (
            completed % 250_000 == 0
            or completed == rounds
        ):
            print(
                f"  {completed:,}/{rounds:,}"
            )

    elapsed = time.time() - start

    print(
        f"Published {mode} sampling completed "
        f"in {elapsed:.1f}s"
    )

    return stats


def raw_test(
    mode: str,
    rounds: int,
):
    cost = 1.0 if mode == "base" else BONUS_COST
    stats = Stats(cost)

    builder = BookBuilder(bet=1.0)

    print(
        f"\nGenerating {rounds:,} RAW "
        f"{mode.upper()} rounds..."
    )

    start = time.time()

    for i in range(1, rounds + 1):
        book = builder.build_round(
            i,
            mode,
        )

        payout = (
            book["payoutMultiplier"]
            / 100.0
        )

        stats.add(
            payout,
            free_spin_trigger=(
                mode == "base"
                and book.get("criteria")
                == "freegame"
            ),
        )

        if (
            i % 100_000 == 0
            or i == rounds
        ):
            elapsed = time.time() - start

            print(
                f"  {i:,}/{rounds:,} "
                f"({elapsed:.1f}s)"
            )

    elapsed = time.time() - start

    print(
        f"Raw {mode} generation completed "
        f"in {elapsed:.1f}s"
    )

    return stats


def main():
    print("=" * 72)
    print("VICE HEIST — MILLION ROUND STRESS TEST")
    print("=" * 72)

    print(f"Rounds per test: {ROUNDS:,}")
    print(f"Seed:            {SEED}")
    print(f"Max win:         {MAX_WIN:,.0f}x")
    print(f"Bonus cost:      {BONUS_COST:.0f}x")

    random.seed(SEED)

    published_rng = random.Random(
        SEED + 10_000
    )

    published_base = published_test(
        "base",
        ROUNDS,
        published_rng,
    )

    published_bonus = published_test(
        "bonus",
        ROUNDS,
        published_rng,
    )

    published_base.report(
        "PUBLISHED WEIGHTED BASE"
    )

    published_bonus.report(
        "PUBLISHED WEIGHTED BONUS BUY"
    )

    raw_base = raw_test(
        "base",
        ROUNDS,
    )

    raw_base.report(
        "RAW ENGINE BASE"
    )

    raw_bonus = raw_test(
        "bonus",
        ROUNDS,
    )

    raw_bonus.report(
        "RAW ENGINE BONUS BUY"
    )

    print()
    print("=" * 72)
    print("FINAL COMPARISON")
    print("=" * 72)

    def rtp(stats):
        return (
            stats.total_payout
            / stats.count
            / stats.cost
            * 100.0
        )

    print(
        f"Published Base RTP:       "
        f"{rtp(published_base):.6f}%"
    )

    print(
        f"Raw Base RTP:             "
        f"{rtp(raw_base):.6f}%"
    )

    print(
        f"Published Bonus RTP:      "
        f"{rtp(published_bonus):.6f}%"
    )

    print(
        f"Raw Bonus RTP:            "
        f"{rtp(raw_bonus):.6f}%"
    )

    print()
    print(
        "NOTE: Published results test the actual weighted "
        "book distribution."
    )

    print(
        "Raw results test the underlying reel/evaluator "
        "model before LUT calibration."
    )


if __name__ == "__main__":
    main()
