"""Reproduce A/B/C using verified production books; never edit production LUTs."""
import argparse
import csv
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import zstandard

from analyze_volatility import distribution

ROOT = Path(__file__).resolve().parents[1]
RESERVED = {'loss', 'tail', 'maxwin'}
CAP = 1_000_000


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def verify_inputs(folder, baseline_report):
    report = json.loads(baseline_report.read_text())
    hashes = report['input_sha256']
    expected = {f'{prefix}_{mode}.{extension}' for mode in ('base', 'bonus')
                for prefix, extension in [('books', 'jsonl.zst'), ('lookUpTable', 'csv')]}
    if set(hashes) != expected:
        raise ValueError('Baseline report must identify all four production input hashes')
    for name, value in hashes.items():
        if digest(folder / name) != value:
            raise ValueError('Production source hash mismatch: ' + name)
    return hashes


def load_mode(folder, mode):
    with (folder / f'lookUpTable_{mode}.csv').open(newline='') as source:
        rows = np.array([tuple(map(int, row)) for row in csv.reader(source)], dtype=np.int64)
    if len(rows) < 100000 or rows.shape[1] != 3:
        raise ValueError('Verified production-size LUT required')
    criteria, free, triggered = [], [], []
    with (folder / f'books_{mode}.jsonl.zst').open('rb') as source:
        with zstandard.ZstdDecompressor().stream_reader(source) as stream:
            for index, line in enumerate(io.TextIOWrapper(stream)):
                book = json.loads(line)
                if (book['id'], book['payoutMultiplier']) != (rows[index, 0], rows[index, 2]):
                    raise ValueError('Book and LUT alignment mismatch')
                ends = [e['amount'] for e in book['events'] if e['type'] == 'freeSpinEnd']
                criteria.append(book['criteria'])
                free.append(ends[0] if ends else 0)
                triggered.append(any(e['type'] == 'freeSpinTrigger' for e in book['events']))
    if len(criteria) != len(rows):
        raise ValueError('Book count mismatch')
    return rows, np.array(criteria), np.array(free, dtype=np.int64), np.array(triggered)


def apportion(values, total):
    """Deterministic largest-remainder rounding; preserve integer mass exactly."""
    floors = np.floor(values).astype(np.int64)
    missing = total - sum(map(int, floors))
    if missing < 0 or missing > len(floors):
        raise ValueError('Invalid apportionment mass')
    order = np.argsort(-(values - floors), kind='stable')
    floors[order[:missing]] += 1
    if np.any(floors < 1):
        raise ValueError('Candidate would remove an outcome')
    return floors


def candidate_weights(rows, reserved, target):
    """Solve the two constraints via exact group mass and scalar log1p tilt."""
    payouts = rows[:, 2] / 100.0
    original = rows[:, 1]
    total = sum(map(int, original))
    ordinary = ~reserved
    mass = sum(map(int, original[ordinary]))
    high = payouts[ordinary] >= 100
    high_mass = (target * total - sum(map(int, original[reserved & (payouts >= 100)]))) / mass
    reserved_payout = sum(int(w) * int(p) for w, p in zip(original[reserved], rows[reserved, 2])) / 100
    mean = (96 * total - reserved_payout) / mass
    if not 0 < high_mass < 1 or not np.any(high) or not np.any(~high):
        raise ValueError('Recovery probability is not feasible')
    feature = np.log1p(payouts[ordinary])
    prior = np.log(original[ordinary].astype(float))

    def probabilities(alpha):
        logits = prior + alpha * feature
        result = np.empty(len(logits))
        for mask, group_mass in [(high, high_mass), (~high, 1 - high_mass)]:
            group = np.exp(logits[mask] - np.max(logits[mask]))
            result[mask] = group * (group_mass / group.sum())
        return result

    lower, upper = -1.0, 1.0
    for _ in range(20):
        if probabilities(lower) @ payouts[ordinary] <= mean:
            break
        lower *= 2
    for _ in range(20):
        if probabilities(upper) @ payouts[ordinary] >= mean:
            break
        upper *= 2
    if not probabilities(lower) @ payouts[ordinary] <= mean <= probabilities(upper) @ payouts[ordinary]:
        raise ValueError('Target mean not bracketed')
    for _ in range(80):
        middle = (lower + upper) / 2
        if probabilities(middle) @ payouts[ordinary] < mean:
            lower = middle
        else:
            upper = middle
    alpha = (lower + upper) / 2
    weights = original.copy()
    weights[ordinary] = apportion(probabilities(alpha) * mass, mass)
    # These are actual integer-weight checks, not floating distribution claims.
    actual = sum(int(w) * int(p) for w, p in zip(weights, rows[:, 2])) / (10000 * total)
    recovered = sum(map(int, weights[payouts >= 100])) / total
    if abs(actual - .96) > 1e-6 or abs(recovered - target) > 1e-6:
        raise ValueError('Integer candidate missed RTP or recovery target')
    if not np.array_equal(weights[reserved], original[reserved]) or sum(map(int, weights)) != total:
        raise ValueError('Reserved weights or total mass changed')
    if np.any(weights <= 0) or total >= 2**64 or rows[:, 2].max() != CAP:
        raise ValueError('Invalid weights or cap')
    capped = rows[:, 2] == CAP
    if not np.array_equal(weights[capped], original[capped]):
        raise ValueError('Maximum-win probability changed')
    return weights, {'log1p_tilt_alpha': alpha, 'recovery_target': target,
                     'rtp': actual, 'reserved_probabilities_unchanged': True}


def metrics(payouts, weights, cost):
    values = defaultdict(int)
    for payout, weight in zip(payouts, weights):
        values[int(payout)] += int(weight)
    result = distribution(values, cost)
    total = sum(values.values())
    returned = sum(p * w for p, w in values.items())
    for label, lower, upper in [('50_to_300_x', 5000, 30000),
                                ('5000_to_10000_x', 500000, CAP)]:
        mass = sum(w for p, w in values.items() if lower <= p <= upper)
        paid = sum(p * w for p, w in values.items() if lower <= p <= upper)
        result[label] = {'probability': mass / total,
                         'mean_contribution_x': paid / (total * 100),
                         'share_of_return': paid / returned if returned else 0}
    return result


def run(folder, baseline_report, output):
    folder, output = folder.resolve(), output.resolve()
    if output == folder or output.is_relative_to(folder) or folder.is_relative_to(output):
        raise ValueError('Experiment output must be isolated from production source')
    hashes = verify_inputs(folder, baseline_report)
    base_rows, _, base_free, base_trigger = load_mode(folder, 'base')
    bonus_rows, criteria, bonus_free, bonus_trigger = load_mode(folder, 'bonus')
    if not np.all(bonus_trigger) or not np.array_equal(bonus_free, bonus_rows[:, 2]):
        raise ValueError('Bonus purchase feature semantics mismatch')
    reserved = np.isin(criteria, list(RESERVED))
    original = bonus_rows[:, 1]
    output.mkdir(parents=True, exist_ok=True)
    report = {'method': 'Existing integer prior weights tilted by alpha*log1p(payout_x) plus >=100x group adjustment; scalar bisection; deterministic largest remainder integer apportionment.',
              'status': 'Analysis candidates only; production weights unchanged.',
              'input_sha256': hashes,
              'baseline_report_sha256': digest(baseline_report),
              'payout_unit': 'ordinary bet multiples; bonus cost 100x; bins inclusive',
              'baseline_bonus': metrics(bonus_rows[:, 2], original, 100),
              'natural_feature': {
                  'unchanged': True,
                  'trigger_probability': sum(map(int, base_rows[base_trigger, 1])) / sum(map(int, base_rows[:, 1])),
                  'complete_round': metrics(base_rows[:, 2], base_rows[:, 1], 1),
                  'conditional_free_spins': metrics(base_free[base_trigger], base_rows[base_trigger, 1], 1)},
              'candidates': {}}
    # Report pool availability for a future mass/mean preserving natural-feature
    # experiment restricted to the same initial award, keeping trigger odds fixed.
    same_award = base_trigger & (base_rows[:, 2] - base_free == 200)
    report['natural_feature']['same_2x_initial_award_pool'] = {
        'books': int(same_award.sum()),
        'medium_50_to_300_books': int((same_award & (base_free >= 5000) & (base_free <= 30000)).sum()),
        'extreme_round_5000_to_10000_books': int((same_award & (base_rows[:, 2] >= 500000)).sum()),
        'low_free_spins_below_50_books': int((same_award & (base_free < 5000)).sum())}
    for name, target in [('A', .30), ('B', .35), ('C', .40)]:
        weights, solver = candidate_weights(bonus_rows, reserved, target)
        destination = output / ('candidate_' + name)
        destination.mkdir(exist_ok=True)
        lut = destination / 'lookUpTable_bonus.csv'
        with lut.open('w', newline='') as file:
            csv.writer(file).writerows((int(i), int(w), int(p)) for (i, _, p), w in zip(bonus_rows, weights))
        result = {'solver': solver, 'metrics': metrics(bonus_rows[:, 2], weights, 100),
                  'lookup_sha256': digest(lut), 'books_sha256': hashes['books_bonus.jsonl.zst']}
        (destination / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
        report['candidates'][name] = result
    # Check source hashes again: experimentation cannot mutate production files.
    verify_inputs(folder, baseline_report)
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', type=Path, default=ROOT / 'release/math')
    parser.add_argument('--baseline-report', type=Path, default=ROOT / 'docs/validation/volatility_report.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'release/experiments/bonus_distribution')
    args = parser.parse_args()
    report = run(args.publish, args.baseline_report, args.output)
    for name, candidate in report['candidates'].items():
        print(name, json.dumps(candidate))
    print('PASS: reproducible isolated candidates; production input hashes unchanged')


if __name__ == '__main__':
    main()
