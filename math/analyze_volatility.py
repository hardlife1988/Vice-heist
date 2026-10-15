"""Exact weighted player-experience metrics, never unweighted book counts.

Run after a production build and exhaustive evaluator audit. All payout figures
are multiples of the ordinary bet; bonus purchase cost is 100 ordinary bets.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from collections import defaultdict
from pathlib import Path
import zstandard

ROOT = Path(__file__).resolve().parents[1]
CAP = 1_000_000


def distribution(values, cost=1):
    weight = sum(values.values())
    if not weight:
        return None
    mean = sum(p * w for p, w in values.items()) / weight / 100
    variance = sum(w * (p / 100 - mean) ** 2 for p, w in values.items()) / weight
    cumulative = 0
    quantiles = {}
    for payout, w in sorted(values.items()):
        cumulative += w
        for name, fraction in [('p10', .1), ('median', .5), ('p90', .9), ('p99', .99)]:
            if name not in quantiles and cumulative >= weight * fraction:
                quantiles[name] = payout / 100
    positive = sum(w for p, w in values.items() if p > 0)
    return {
        'mean_x': mean, **{k + '_x': v for k, v in quantiles.items()},
        'standard_deviation_x': math.sqrt(variance),
        'standard_deviation_per_cost': math.sqrt(variance) / cost,
        'hit_probability': positive / weight,
        'mean_positive_win_x': mean * weight / positive if positive else 0,
        'zero_probability': values.get(0, 0) / weight,
        'below_cost_probability': sum(w for p, w in values.items() if p < cost * 100) / weight,
        'break_even_probability': values.get(cost * 100, 0) / weight,
        'profit_probability': sum(w for p, w in values.items() if p > cost * 100) / weight,
        'tails_at_least_x': {str(x): sum(w for p, w in values.items() if p >= x * 100) / weight for x in [100, 500, 1000, 10000]},
        'maximum_x': max(values) / 100,
        'rtp_share_from_at_least_x': {str(x): sum(p * w for p, w in values.items() if p >= x * 100) / sum(p * w for p, w in values.items()) if mean else 0 for x in [100, 500, 1000, 10000]},
    }


def analyze(folder, mode, cost):
    with (folder / f'lookUpTable_{mode}.csv').open(newline='') as source:
        rows = [tuple(map(int, row)) for row in csv.reader(source)]
    assert len(rows) >= 100000, 'Production outcomes required'
    totals, base, free = defaultdict(int), defaultdict(int), defaultdict(int)
    categories = {}
    trigger_weight = 0
    cap_books = []
    largest = []
    count = 0
    with (folder / f'books_{mode}.jsonl.zst').open('rb') as source, zstandard.ZstdDecompressor().stream_reader(source) as stream:
        for line in io.TextIOWrapper(stream):
            book = json.loads(line)
            identity, weight, payout = rows[count]
            assert (book['id'], book['payoutMultiplier']) == (identity, payout)
            assert weight > 0 and 0 <= payout <= CAP
            events = book['events']
            finals = [e['amount'] for e in events if e['type'] == 'finalWin']
            assert finals == [payout]
            paid_spins = sum(e['totalWin'] for e in events if e['type'] == 'winInfo')
            assert paid_spins == payout, f'Book {identity}: spin payments disagree'
            assert all(0 <= e['amount'] <= CAP for e in events if e['type'] in ('setTotalWin', 'finalWin', 'freeSpinEnd', 'wincap'))
            caps = [e for e in events if e['type'] == 'wincap']
            assert bool(caps) == (payout == CAP)
            free_end = [e['amount'] for e in events if e['type'] == 'freeSpinEnd']
            assert len(free_end) <= 1
            free_paid = free_end[0] if free_end else 0
            assert 0 <= free_paid <= payout
            totals[payout] += weight
            if mode == 'base':
                base[payout - free_paid] += weight
            triggered = any(e['type'] == 'freeSpinTrigger' for e in events)
            if triggered:
                trigger_weight += weight
                free[free_paid] += weight
            if mode == 'bonus':
                assert triggered, 'Purchased bonus must enter free spins'
                assert free_paid == payout
            category = book['criteria']
            entry = categories.setdefault(category, {'books': 0, 'weight': 0, 'maximum_x': 0})
            entry['books'] += 1; entry['weight'] += weight
            entry['maximum_x'] = max(entry['maximum_x'], payout / 100)
            sample = {'id': identity, 'payout_x': payout / 100, 'probability': weight, 'criteria': category, 'free_spins_played': sum(e['type'] == 'updateFreeSpin' for e in events), 'cap_event': bool(caps)}
            largest.append(sample)
            largest.sort(key=lambda item: (-item['payout_x'], item['id']))
            del largest[10:]
            if payout == CAP:
                cap_books.append(sample.copy())
            count += 1
    assert count == len(rows)
    total_weight = sum(totals.values())
    for sample in largest + cap_books:
        sample['probability'] /= total_weight
    for entry in categories.values():
        entry['probability'] = entry.pop('weight') / total_weight
    return {
        'books': count, 'total_weight': total_weight, 'cost_x': cost,
        'complete_round': distribution(totals, cost),
        'initial_base_spin': distribution(base) if mode == 'base' else None,
        'free_spin_trigger_probability': trigger_weight / total_weight,
        'free_spins_only_conditional_on_trigger': distribution(free, cost if mode == 'bonus' else 1),
        'categories': categories, 'largest_outcomes': largest,
        'cap_outcomes': cap_books, 'all_outcome_caps_and_paid_totals_verified': True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', type=Path, default=ROOT / 'release/math')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/validation/volatility_report.json')
    args = parser.parse_args()
    report = {
        'method': 'Exact probability-weighted production LUT and event-book analysis; no Monte Carlo sampling.',
        'payout_unit': 'multiples of ordinary total bet; bonus costs 100x',
        'limitations': 'These metrics describe the finite published distribution, including explicitly weighted tail scenarios. They do not establish independent reel-RNG odds, platform certification, or session guarantees.',
        'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.publish.iterdir()) if p.name.startswith(('books_', 'lookUpTable_'))},
        'modes': {mode: analyze(args.publish, mode, cost) for mode, cost in [('base', 1), ('bonus', 100)]},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    for mode, result in report['modes'].items():
        print(mode, json.dumps({k: v for k, v in result.items() if k not in ('largest_outcomes', 'cap_outcomes', 'categories')}))
    print('PASS: every published outcome is capped and reconciles to its paid spin events')


if __name__ == '__main__':
    main()
