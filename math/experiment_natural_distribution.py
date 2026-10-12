"""Isolated natural-feature tail transfers with exact integer mass and return."""
import argparse
import csv
import json
from fractions import Fraction
from pathlib import Path

import numpy as np

from experiment_bonus_distribution import CAP, ROOT, digest, load_mode, metrics, verify_inputs


def apportion_delta(weights, total):
    """Exact largest-remainder integer allocation, allowing zero adjustments."""
    weights = list(map(int, weights))
    denominator = sum(weights)
    if total < 0 or denominator <= 0:
        raise ValueError('Invalid allocation')
    floors = [w * total // denominator for w in weights]
    order = sorted(range(len(weights)), key=lambda i: (-(weights[i] * total % denominator), i))
    for index in order[:total - sum(floors)]:
        floors[index] += 1
    return np.array(floors, dtype=np.int64)


def paid_sum(payouts, weights):
    return sum(int(p) * int(w) for p, w in zip(payouts, weights))


def repair_return(payouts, weights, eligible, difference):
    """Repair rounding by a mass-neutral transfer within low feature outcomes.

    Fail rather than relax constraints if no payout pair can absorb the exact
    difference with positive remaining weights.
    """
    if not difference:
        return None
    representatives = {}
    for index in np.flatnonzero(eligible):
        payout = int(payouts[index])
        current = representatives.get(payout)
        if current is None or weights[index] > weights[current]:
            representatives[payout] = int(index)
    values = sorted(representatives)
    pairs = [(b - a, a, b) for a, b in zip(values, values[1:])]
    for step, low, high in sorted(pairs):
        if difference % step:
            continue
        adjustment = difference // step
        low_index, high_index = representatives[low], representatives[high]
        if weights[low_index] - adjustment < 1 or weights[high_index] + adjustment < 1:
            continue
        weights[low_index] -= adjustment
        weights[high_index] += adjustment
        return {'low_book_index': low_index, 'high_book_index': high_index,
                'payout_step_units': step, 'weight_to_high': adjustment}
    raise ValueError('Exact integer return repair is infeasible within low outcomes')


def natural_candidate(rows, free, triggered, fraction):
    fraction = Fraction(fraction)
    if not 0 < fraction < 1:
        raise ValueError('Donor reduction must be strictly between zero and one')
    payout, original = rows[:, 2], rows[:, 1]
    pool = triggered & (payout - free == 200)
    donors = pool & (payout >= 500000) & (payout < CAP)
    medium = pool & (free >= 5000) & (free <= 30000)
    low = pool & (free < 5000)
    if not all(np.any(mask) for mask in (donors, medium, low)):
        raise ValueError('Required donor, medium or low pool is empty')
    removed_mass = round(sum(map(int, original[donors])) * fraction)
    removed = apportion_delta(original[donors], removed_mass)
    removed_paid = paid_sum(payout[donors], removed)
    low_mass, medium_mass = sum(map(int, original[low])), sum(map(int, original[medium]))
    low_mean = Fraction(paid_sum(payout[low], original[low]), low_mass)
    medium_mean = Fraction(paid_sum(payout[medium], original[medium]), medium_mass)
    if medium_mean <= low_mean:
        raise ValueError('Medium mean must exceed low mean')
    addition = round((removed_paid - removed_mass * low_mean) / (medium_mean - low_mean))
    removal = addition - removed_mass
    if addition <= 0 or removal < 0 or removal >= low_mass - int(low.sum()):
        raise ValueError('Balanced transfer would exhaust low outcomes')
    weights = original.copy()
    weights[donors] -= removed
    weights[medium] += apportion_delta(original[medium], addition)
    weights[low] -= apportion_delta(original[low], removal)
    if np.any(weights < 1):
        raise ValueError('Balanced transfer would remove an outcome')
    original_paid = paid_sum(payout, original)
    repair = repair_return(payout, weights, low, original_paid - paid_sum(payout, weights))
    original_mass = sum(map(int, original))
    # Exact Python-integer checks, no tolerance on mass or expected return.
    if (sum(map(int, weights)) != original_mass or paid_sum(payout, weights) != original_paid
            or sum(map(int, weights[triggered])) != sum(map(int, original[triggered]))
            or not np.array_equal(weights[~pool], original[~pool])
            or not np.array_equal(weights[payout == CAP], original[payout == CAP])
            or np.any(weights < 1)):
        raise ValueError('Natural candidate violated exact conservation constraints')
    if sum(map(int, weights[medium])) <= sum(map(int, original[medium])):
        raise ValueError('Medium payout frequency did not increase')
    if payout.max() != CAP or abs(original_paid / (100 * original_mass) - .96) > 1e-6:
        raise ValueError('Baseline RTP or maximum is invalid')
    return weights, {
        'donor_fraction': str(fraction), 'donor_books': int(donors.sum()),
        'donor_weight_removed': removed_mass, 'medium_weight_added': addition,
        'low_weight_removed': removal, 'rounding_repair': repair,
        'total_weight': original_mass, 'weighted_payout_units': original_paid,
        'rtp': original_paid / (100 * original_mass),
        'integer_return_and_mass_preserved_exactly': True,
        'cap_probability_and_trigger_probability_preserved_exactly': True,
        'initial_base_spin_distribution_preserved_exactly': True}


def run(folder, baseline_report, output):
    folder, output = folder.resolve(), output.resolve()
    if output == folder or output.is_relative_to(folder) or folder.is_relative_to(output):
        raise ValueError('Experiment output must be isolated from production source')
    hashes = verify_inputs(folder, baseline_report)
    rows, _, free, triggered = load_mode(folder, 'base')
    original = rows[:, 1]
    total = sum(map(int, original))

    def summarize(weights):
        return {'complete_round': metrics(rows[:, 2], weights, 1),
                'conditional_free_spins': metrics(free[triggered], weights[triggered], 1),
                'trigger_probability': sum(map(int, weights[triggered])) / total}

    report = {'method': 'Restrict transfers to triggered books with an identical 2x initial award. Reduce noncap >=5000x full-round donor weight, add medium50–300x free-spin weight and remove below50x free-spin weight using mass/mean balance. Exact largest remainder and a mass-neutral low-outcome repair preserve integer expected payout.',
              'status': 'Analysis only; production source and bonus A/B/C weights unchanged.',
              'input_sha256': hashes, 'baseline_report_sha256': digest(baseline_report),
              'payout_unit': 'ordinary bet multiples; bins inclusive; full-round tail includes initial award',
              'baseline': summarize(original), 'candidates': {}}
    output.mkdir(parents=True, exist_ok=True)
    for name, fraction in [('N25', Fraction(1, 4)), ('N50', Fraction(1, 2)), ('N75', Fraction(3, 4))]:
        weights, solver = natural_candidate(rows, free, triggered, fraction)
        destination = output / ('candidate_' + name)
        destination.mkdir(exist_ok=True)
        lut = destination / 'lookUpTable_base.csv'
        with lut.open('w', newline='') as file:
            csv.writer(file).writerows((int(i), int(w), int(p)) for (i, _, p), w in zip(rows, weights))
        result = {'solver': solver, 'metrics': summarize(weights),
                  'lookup_sha256': digest(lut), 'books_sha256': hashes['books_base.jsonl.zst']}
        (destination / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
        report['candidates'][name] = result
    verify_inputs(folder, baseline_report)
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', type=Path, default=ROOT / 'release/math')
    parser.add_argument('--baseline-report', type=Path, default=ROOT / 'docs/validation/volatility_report.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'release/experiments/natural_distribution')
    args = parser.parse_args()
    report = run(args.publish, args.baseline_report, args.output)
    for name, candidate in report['candidates'].items():
        print(name, json.dumps(candidate))
    print('PASS: exact integer mass/return, trigger odds, initial awards and cap probability conserved')


if __name__ == '__main__':
    main()
