#!/usr/bin/env python3

import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATH = os.path.join(ROOT, "math")
sys.path.insert(0, MATH)

from game_config import GameConfig
from reel_engine import ReelEngine
from win_evaluator import WinEvaluator


ROUNDS = int(os.environ.get("VICE_HEIST_AUDIT_ROUNDS", "100000"))
SEED = int(os.environ.get("VICE_HEIST_AUDIT_SEED", "1988"))


def main():
    random.seed(SEED)

    config = GameConfig()
    engine = ReelEngine(config)
    evaluator = WinEvaluator(config)

    base_line = 0.0
    base_scatter = 0.0
    feature_return = 0.0

    triggers = 0
    total_free_spins = 0

    bonus_line = 0.0
    bonus_scatter = 0.0

    print("=" * 68)
    print("VICE HEIST — COMPONENT RTP AUDIT")
    print("=" * 68)
    print(f"Base rounds:       {ROUNDS:,}")
    print(f"Bonus spin sample: {ROUNDS:,}")
    print(f"Seed:              {SEED}")
    print()

    # ------------------------------------------------------------
    # BASE GAME
    # ------------------------------------------------------------

    for i in range(1, ROUNDS + 1):
        grid = engine.spin_reels(mode="base")

        result = evaluator.evaluate_spin(
            grid,
            1.0,
            1.0,
        )

        line_win = sum(
            win["win"]
            for win in result["payline_wins"]
        )

        base_line += line_win
        base_scatter += result["scatter_win"]

        if result["triggers_free_spins"]:
            triggers += 1

            for _ in range(config.free_spins_count):
                fs_grid = engine.spin_reels(
                    mode="natural_bonus"
                )

                fs_result = evaluator.evaluate_spin(
                    fs_grid,
                    1.0,
                    config.free_spins_multiplier,
                )

                feature_return += fs_result["total_win"]
                total_free_spins += 1

        if i % 25000 == 0:
            print(
                f"Base progress: "
                f"{i:,}/{ROUNDS:,}"
            )

    # ------------------------------------------------------------
    # BONUS REEL SINGLE-SPIN COMPONENTS
    # ------------------------------------------------------------

    for i in range(1, ROUNDS + 1):
        grid = engine.spin_reels(mode="bonus_buy")

        result = evaluator.evaluate_spin(
            grid,
            1.0,
            config.free_spins_multiplier,
        )

        line_win = sum(
            win["win"]
            for win in result["payline_wins"]
        )

        bonus_line += line_win
        bonus_scatter += result["scatter_win"]

        if i % 25000 == 0:
            print(
                f"Bonus progress: "
                f"{i:,}/{ROUNDS:,}"
            )

    # ------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------

    base_line_rtp = base_line / ROUNDS
    base_scatter_rtp = base_scatter / ROUNDS
    feature_rtp = feature_return / ROUNDS

    raw_base_rtp = (
        base_line_rtp
        + base_scatter_rtp
        + feature_rtp
    )

    trigger_rate = triggers / ROUNDS

    bonus_line_per_spin = bonus_line / ROUNDS
    bonus_scatter_per_spin = bonus_scatter / ROUNDS

    bonus_total_per_spin = (
        bonus_line_per_spin
        + bonus_scatter_per_spin
    )

    expected_bonus_buy = (
        bonus_total_per_spin
        * config.free_spins_count
    )

    bonus_buy_rtp = (
        expected_bonus_buy
        / config.bonus_buy_cost
    )

    print()
    print("=" * 68)
    print("BASE GAME COMPONENTS")
    print("=" * 68)

    print(
        f"Base payline RTP:       "
        f"{base_line_rtp * 100:.4f}%"
    )

    print(
        f"Base scatter RTP:       "
        f"{base_scatter_rtp * 100:.4f}%"
    )

    print(
        f"Natural feature RTP:    "
        f"{feature_rtp * 100:.4f}%"
    )

    print("-" * 68)

    print(
        f"TOTAL RAW BASE RTP:     "
        f"{raw_base_rtp * 100:.4f}%"
    )

    print()
    print(
        f"Feature triggers:       "
        f"{triggers:,}/{ROUNDS:,}"
    )

    print(
        f"Feature trigger rate:   "
        f"{trigger_rate * 100:.4f}%"
    )

    if triggers:
        print(
            f"Trigger frequency:      "
            f"1 in {1 / trigger_rate:.2f}"
        )

        print(
            f"Average feature win:    "
            f"{feature_return / triggers:.4f}x"
        )

    print(
        f"Free spins simulated:   "
        f"{total_free_spins:,}"
    )

    print()
    print("=" * 68)
    print("FREE-SPIN / BONUS COMPONENTS")
    print("=" * 68)

    print(
        f"Paylines per FS:        "
        f"{bonus_line_per_spin:.4f}x"
    )

    print(
        f"Scatter per FS:         "
        f"{bonus_scatter_per_spin:.4f}x"
    )

    print(
        f"Total return per FS:    "
        f"{bonus_total_per_spin:.4f}x"
    )

    print(
        f"Expected 10-spin bonus: "
        f"{expected_bonus_buy:.4f}x"
    )

    print(
        f"Bonus Buy cost:         "
        f"{config.bonus_buy_cost:.2f}x"
    )

    print(
        f"RAW BONUS BUY RTP:      "
        f"{bonus_buy_rtp * 100:.4f}%"
    )

    print()
    print("=" * 68)
    print("CONTRIBUTION TO BASE RTP")
    print("=" * 68)

    total = raw_base_rtp

    for name, value in (
        ("Base paylines", base_line_rtp),
        ("Base scatters", base_scatter_rtp),
        ("Free-spin feature", feature_rtp),
    ):
        share = (
            value / total * 100
            if total > 0
            else 0
        )

        print(
            f"{name:<20} "
            f"{value * 100:>9.4f}% RTP "
            f"({share:>6.2f}% of return)"
        )


if __name__ == "__main__":
    main()
