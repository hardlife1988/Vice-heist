#!/usr/bin/env python3
"""Audit generated Vice Heist math without modifying the bundle."""

from __future__ import annotations

import csv
import json
import os
from statistics import median


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLISH = os.path.join(ROOT, "math", "library", "publish_files")

BASE_COST = 1.0
BONUS_COST = 100.0
MAX_WIN = 10_000.0


def load_books(filename: str) -> list[dict]:
    path = os.path.join(PUBLISH, filename)

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing generated book file: {path}")

    books = []

    with open(path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                books.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {filename}"
                ) from exc

    if not books:
        raise ValueError(f"No books found in {filename}")

    return books


def load_lut(filename: str) -> dict[int, int]:
    path = os.path.join(PUBLISH, filename)

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing LUT: {path}")

    weights = {}

    with open(path, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)

        for line_number, row in enumerate(reader, start=1):
            if len(row) < 3:
                raise ValueError(
                    f"Invalid LUT row {line_number} in {filename}: {row}"
                )

            book_id = int(row[0])
            weight = int(row[1])

            if weight <= 0:
                raise ValueError(
                    f"Non-positive LUT weight for book {book_id}"
                )

            if book_id in weights:
                raise ValueError(
                    f"Duplicate LUT book id: {book_id}"
                )

            weights[book_id] = weight

    return weights


def payout_x(book: dict) -> float:
    """payoutMultiplier uses 100 = 1x ordinary bet."""
    return float(book["payoutMultiplier"]) / 100.0


def validate_alignment(
    books: list[dict],
    weights: dict[int, int],
) -> None:
    book_ids = {int(book["id"]) for book in books}
    lut_ids = set(weights)

    missing = book_ids - lut_ids
    extra = lut_ids - book_ids

    if missing:
        raise ValueError(
            f"{len(missing)} books are missing LUT weights"
        )

    if extra:
        raise ValueError(
            f"{len(extra)} LUT ids have no matching book"
        )


def raw_rtp(
    books: list[dict],
    cost: float,
) -> float:
    average_payout = sum(
        payout_x(book) for book in books
    ) / len(books)

    return average_payout / cost


def weighted_rtp(
    books: list[dict],
    weights: dict[int, int],
    cost: float,
) -> float:
    numerator = 0.0
    denominator = 0

    for book in books:
        weight = weights[int(book["id"])]
        numerator += payout_x(book) * weight
        denominator += weight

    return numerator / (cost * denominator)


def raw_hit_frequency(books: list[dict]) -> float:
    return sum(
        payout_x(book) > 0
        for book in books
    ) / len(books)


def weighted_hit_frequency(
    books: list[dict],
    weights: dict[int, int],
) -> float:
    winning_weight = 0
    total_weight = 0

    for book in books:
        weight = weights[int(book["id"])]
        total_weight += weight

        if payout_x(book) > 0:
            winning_weight += weight

    return winning_weight / total_weight


def weighted_free_spin_frequency(
    books: list[dict],
    weights: dict[int, int],
) -> float:
    feature_weight = 0
    total_weight = 0

    for book in books:
        weight = weights[int(book["id"])]
        total_weight += weight

        if book.get("criteria") == "freegame":
            feature_weight += weight

    return feature_weight / total_weight


def effective_book_count(
    books: list[dict],
    weights: dict[int, int],
) -> float:
    values = [
        weights[int(book["id"])]
        for book in books
    ]

    total = sum(values)

    return (
        total * total
        / sum(weight * weight for weight in values)
    )


def weighted_average_payout(
    books: list[dict],
    weights: dict[int, int],
) -> float:
    numerator = 0.0
    denominator = 0

    for book in books:
        weight = weights[int(book["id"])]
        numerator += payout_x(book) * weight
        denominator += weight

    return numerator / denominator


def top_payouts(
    books: list[dict],
    limit: int = 10,
) -> list[dict]:
    return sorted(
        books,
        key=payout_x,
        reverse=True,
    )[:limit]


def audit_mode(
    name: str,
    books_filename: str,
    lut_filename: str,
    cost: float,
    show_fs_frequency: bool = False,
) -> None:
    books = load_books(books_filename)
    weights = load_lut(lut_filename)

    validate_alignment(books, weights)

    payouts = [
        payout_x(book)
        for book in books
    ]

    raw = raw_rtp(books, cost)
    weighted = weighted_rtp(
        books,
        weights,
        cost,
    )

    raw_hit = raw_hit_frequency(books)
    weighted_hit = weighted_hit_frequency(
        books,
        weights,
    )

    effective = effective_book_count(
        books,
        weights,
    )

    maximum = max(payouts)
    average = sum(payouts) / len(payouts)
    weighted_average = weighted_average_payout(
        books,
        weights,
    )

    print()
    print("=" * 64)
    print(name.upper())
    print("=" * 64)

    print(f"Books:                    {len(books):,}")
    print(f"Cost:                     {cost:.2f}x")
    print(f"Raw RTP:                  {raw * 100:.4f}%")
    print(f"Weighted RTP:             {weighted * 100:.4f}%")
    print(f"Raw hit frequency:        {raw_hit * 100:.2f}%")
    print(f"Weighted hit frequency:   {weighted_hit * 100:.2f}%")
    print(f"Raw average payout:       {average:.4f}x")
    print(f"Weighted average payout:  {weighted_average:.4f}x")
    print(f"Median book payout:       {median(payouts):.4f}x")
    print(f"Maximum observed payout:  {maximum:.4f}x")
    print(
        f"Effective books:          "
        f"{effective:.1f}/{len(books)}"
    )

    if show_fs_frequency:
        fs_frequency = weighted_free_spin_frequency(
            books,
            weights,
        )

        print(
            f"Weighted free-spin rate:  "
            f"{fs_frequency * 100:.4f}%"
        )

    print()
    print("Top 10 generated payouts:")

    for rank, book in enumerate(
        top_payouts(books),
        start=1,
    ):
        print(
            f"  {rank:>2}. "
            f"book {int(book['id']):>5}  "
            f"{payout_x(book):>10.4f}x  "
            f"weight={weights[int(book['id'])]}"
        )

    if maximum > MAX_WIN:
        raise RuntimeError(
            f"{name}: observed payout {maximum:.4f}x "
            f"exceeds {MAX_WIN:.0f}x max win"
        )


def main() -> None:
    print("VICE HEIST MATH AUDIT")
    print(f"Bundle: {PUBLISH}")

    audit_mode(
        name="Base",
        books_filename="books_base.jsonl",
        lut_filename="lookUpTable_base.csv",
        cost=BASE_COST,
        show_fs_frequency=True,
    )

    audit_mode(
        name="Bonus Buy",
        books_filename="books_bonus.jsonl",
        lut_filename="lookUpTable_bonus.csv",
        cost=BONUS_COST,
    )

    print()
    print("=" * 64)
    print("AUDIT COMPLETE")
    print("=" * 64)
    print(
        "No generated payout exceeded the configured "
        f"{MAX_WIN:.0f}x max-win limit."
    )


if __name__ == "__main__":
    main()
