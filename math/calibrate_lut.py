"""Deterministic integer LUT calibration for a finite, pre-generated book set.

This calibrates BOOK SELECTION, not the independent HMAC reel generator.
"""
from __future__ import annotations

import math


TARGET_RTP = 0.96
TOLERANCE = 0.005  # Half a percentage point.


def weighted_rtp(books: list[dict], weights: list[int], cost: float) -> float:
    if not books or len(books) != len(weights) or cost <= 0:
        raise ValueError("Invalid books, weights, or cost")
    if any(not isinstance(w, int) or w < 1 for w in weights):
        raise ValueError("Every book must have a positive integer weight")
    return sum(b["payoutMultiplier"] * w for b, w in zip(books, weights)) / (
        100.0 * cost * sum(weights)
    )


def calibrate(
    books: list[dict],
    cost: float,
    target: float = TARGET_RTP,
    tolerance: float = TOLERANCE,
    weight_scale: int = 100_000,
) -> tuple[list[int], float]:
    """Exponential tilt of book probabilities; retain every book with weight >= 1.

    Raises rather than inventing an RTP if generated outcomes cannot bracket
    the target. Very skewed distributions are reported by the caller.
    """
    if not books or cost <= 0 or not 0 < target < 1:
        raise ValueError("Invalid calibration parameters")
    payouts = [b["payoutMultiplier"] / (100.0 * cost) for b in books]
    lo, hi = min(payouts), max(payouts)
    if not lo <= target <= hi:
        raise ValueError(
            f"Target {target:.2%} unattainable with existing outcomes: "
            f"range {lo:.2%} to {hi:.2%}. Generate a richer book set."
        )
    if max(payouts) == min(payouts):
        weights = [1] * len(books)
        actual = weighted_rtp(books, weights, cost)
        if abs(actual - target) > tolerance:
            raise ValueError("All books have identical payouts outside tolerance")
        return weights, actual

    # Normalize to [0,1] so extreme bonus payouts do not overflow exp().
    values = [(p - lo) / (hi - lo) for p in payouts]

    def distribution(beta: float) -> list[float]:
        logits = [beta * v for v in values]
        offset = max(logits)
        exps = [math.exp(x - offset) for x in logits]
        denom = sum(exps)
        return [x / denom for x in exps]

    def expectation(beta: float) -> float:
        probabilities = distribution(beta)
        return sum(p * q for p, q in zip(payouts, probabilities))

    lower, upper = -1.0, 1.0
    while expectation(lower) > target:
        lower *= 2
        if lower < -4096:
            raise ValueError("Could not bracket target at low end")
    while expectation(upper) < target:
        upper *= 2
        if upper > 4096:
            raise ValueError("Could not bracket target at high end")

    for _ in range(80):
        mid = (lower + upper) / 2
        if expectation(mid) < target:
            lower = mid
        else:
            upper = mid

    probabilities = distribution((lower + upper) / 2)
    weights = [max(1, round(p * weight_scale)) for p in probabilities]
    actual = weighted_rtp(books, weights, cost)

    # Increase integer precision if rounding disturbed the target.
    for scale in (1_000_000, 10_000_000, 100_000_000):
        if abs(actual - target) <= tolerance:
            break
        weights = [max(1, round(p * scale)) for p in probabilities]
        actual = weighted_rtp(books, weights, cost)

    if abs(actual - target) > tolerance:
        raise ValueError(
            f"Integer LUT calibration missed target: {actual:.4%} "
            f"(target {target:.4%})"
        )
    return weights, actual


def effective_book_count(weights: list[int]) -> float:
    """Inverse Simpson concentration; useful for spotting overly narrow LUTs."""
    total = sum(weights)
    return total * total / sum(w * w for w in weights)
