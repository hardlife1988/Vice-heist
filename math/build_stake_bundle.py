#!/usr/bin/env python3
"""Build an auditable RGS package. --release generates 100,000 books per mode.

SDK is optional; formats and events follow pinned engineio/math-sdk contracts.
All math is normalized to one ordinary bet. Wallet currency is applied later.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import os
import random
import shutil
import time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import zstandard as zstd
from game_config import GameConfig
from paytable import Paytable, Symbol
from reel_engine import ReelEngine
from win_evaluator import WinEvaluator
from calibrate_lut import calibrate, weighted_rtp, effective_book_count

ROOT = str(Path(__file__).resolve().parents[1])
OUT = os.path.join(ROOT, 'math/library/publish_files')
DIST = os.path.join(ROOT, 'dist')
STATIC = os.path.join(ROOT, 'static')
SDK_REVISION = 'a6dccd86de740cc5d318079483cb6204cc5c19bc'
BET_MICROS = [10000, 20000, 50000, 100000, 200000, 400000, 1000000,
              2000000, 5000000, 10000000, 20000000, 50000000, 100000000]
MAX_UNITS = 1_000_000
TAILS = [('loss', 0, 0), ('maxwin', 10, 0)] + [
    ('tail', wild, books) for wild in range(4) for books in range(1, 11-wild)]


def to_cents(amount):
    """Historical name: integer hundredths of the ordinary bet, not money."""
    return int((Decimal(str(amount))*100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def board_from_grid(grid):
    return [[{'name': grid[row][reel].value} for row in range(3)] for reel in range(5)]


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    last = None
    for attempt in range(5):
        try:
            target.write_bytes(data)
            if target.stat().st_size != len(data):
                raise OSError('Short write: ' + str(target))
            return
        except OSError as exc:
            last = exc
            time.sleep(0.3 * (attempt + 1))
    raise OSError(f'Could not copy {source} to {target}: {last}')


def copy_frontend():
    names = ('index.html', 'style.css', 'game.js', 'money.js', 'rgs.js', 'audio.js')
    missing = [os.path.join(STATIC, n) for n in names if not Path(STATIC, n).is_file()]
    if not Path(STATIC, 'assets').is_dir():
        missing.append(os.path.join(STATIC, 'assets'))
    if missing:
        raise FileNotFoundError('Missing frontend inputs: ' + ', '.join(missing))
    Path(DIST).mkdir(parents=True, exist_ok=True)
    for name in names:
        copy_file(Path(STATIC, name), Path(DIST, name))
    for source in Path(STATIC, 'assets').rglob('*'):
        if source.is_file() and source.name != '.gitkeep':
            copy_file(source, Path(DIST, 'assets', source.relative_to(Path(STATIC, 'assets'))))
    for placeholder in Path(DIST, 'assets').rglob('.gitkeep'):
        if placeholder.is_file():
            placeholder.unlink()


class BookBuilder:
    def __init__(self, bet=1.0):
        if not math.isfinite(bet) or bet <= 0: raise ValueError('Bet must be positive and finite')
        self.bet = bet  # Kept for callers; books always use normalized units.
        self.config = GameConfig()
        self.engine = ReelEngine(self.config)
        self.evaluator = WinEvaluator(self.config)

    def _grid(self, reel_mode, free_index):
        if self.scenario is None: return self.engine.spin_reels(mode=reel_mode)
        kind, wild, books = self.scenario
        loss = [[Symbol.CLUB, Symbol.SPADE, Symbol.HEART, Symbol.CLUB, Symbol.SPADE] for _ in range(3)]
        if kind == 'loss': return loss
        if reel_mode == 'base':
            loss[0][:3] = [Symbol.SCATTER]*3
            return loss
        symbol = Symbol.WILD if free_index < wild else Symbol.BOOK if free_index < wild+books else None
        return [[symbol]*5 for _ in range(3)] if symbol else loss

    def _spin(self, events, mode, multiplier, free_index=0):
        grid = self._grid(mode, free_index)
        result = self.evaluator.evaluate_spin(grid, 1.0, multiplier)
        game_type = 'basegame' if mode == 'base' else 'freegame'
        events.append({'index': len(events), 'type': 'reveal', 'board': board_from_grid(grid),
                       'paddingPositions': [0]*5, 'gameType': game_type, 'anticipation': [0]*5})
        remaining = MAX_UNITS-self.total
        wins = []
        for line in result['payline_wins']:
            raw = to_cents(line['win'])
            paid = min(raw, remaining)
            if paid:
                positions = [{'reel': r, 'row': Paytable.PAYLINES[line['payline']][r]} for r in range(line['count'])]
                wins.append({'symbol': line['symbol_key'], 'kind': line['count'], 'win': paid,
                             'positions': positions, 'meta': {'payline': line['payline'], 'uncappedWin': raw}})
                remaining -= paid
        scatter = min(to_cents(result['scatter_win']), remaining)
        if scatter:
            wins.append({'symbol': 'S', 'kind': result['scatter_count'], 'win': scatter,
                         'positions': [], 'meta': {'scatter': True}})
        spin = sum(w['win'] for w in wins)
        self.total += spin
        if spin:
            events.append({'index': len(events), 'type': 'winInfo', 'totalWin': spin, 'wins': wins})
            events.append({'index': len(events), 'type': 'setWin', 'amount': spin, 'winLevel': win_level(spin)})
        events.append({'index': len(events), 'type': 'setTotalWin', 'amount': self.total})
        if self.total == MAX_UNITS:
            events.append({'index': len(events), 'type': 'wincap', 'amount': self.total})
        return grid, result, spin

    def build_round(self, book_id, mode, scenario=None):
        if mode not in ('base', 'bonus'): raise ValueError('Unknown book mode')
        self.scenario = scenario
        self.total = 0
        events = []
        base = free = 0
        feature = mode == 'bonus'
        positions = []
        if mode == 'base':
            grid, result, base = self._spin(events, 'base', 1)
            feature = result['triggers_free_spins']
            positions = scatter_positions(grid)
        if feature and self.total < MAX_UNITS:
            awarded = self.config.free_spins_count
            events.append({'index': len(events), 'type': 'freeSpinTrigger', 'totalFs': awarded,
                           'positions': positions, 'multiplier': self.config.free_spins_multiplier})
            if mode == 'bonus': events.append({'index': len(events), 'type': 'enterBonus', 'reason': 'bonusBuy'})
            mult = self.config.free_spins_multiplier
            played = 0
            reel_mode = 'bonus_buy' if mode == 'bonus' else 'natural_bonus'
            while played < awarded and self.total < MAX_UNITS:
                played += 1
                events.append({'index': len(events), 'type': 'updateFreeSpin', 'amount': played,
                               'total': awarded, 'multiplier': mult})
                events.append({'index': len(events), 'type': 'setMultiplier', 'amount': mult})
                grid, result, spin = self._spin(events, reel_mode, mult, played - 1)
                free += spin
                if self.total >= MAX_UNITS:
                    break
                if spin and mult < self.config.free_spins_multiplier_cap:
                    mult += 1
                extra = retrigger_spins(result['scatter_count'], awarded, self.config)
                if extra:
                    awarded += extra
                    events.append({'index': len(events), 'type': 'freeSpinRetrigger', 'extra': extra,
                                   'totalFs': awarded, 'positions': scatter_positions(grid)})
            events.append({'index': len(events), 'type': 'freeSpinEnd', 'amount': free, 'winLevel': win_level(free)})
        events.append({'index': len(events), 'type': 'finalWin', 'amount': self.total, 'winLevel': win_level(self.total)})
        assert base + free == self.total and self.total % 10 == 0
        return {'id': book_id, 'payoutMultiplier': self.total, 'events': events,
                'criteria': scenario[0] if scenario else 'freegame' if feature else 'basegame',
                'baseGameWins': base / 100, 'freeGameWins': free / 100}


def scatter_positions(grid):
    return [{'reel': reel, 'row': row} for row in range(3) for reel in range(5) if grid[row][reel] == Symbol.SCATTER]


def retrigger_spins(scatter_count, awarded, config):
    """+3 spins for every 3 scatters, never past the feature cap."""
    room = config.free_spins_max - awarded
    if room <= 0 or scatter_count < config.free_spins_trigger:
        return 0
    extra = (scatter_count // config.free_spins_trigger) * config.free_spins_retrigger
    return min(extra, room)


def win_level(units):
    multiple = units / 100
    if multiple >= 100: return 5
    if multiple >= 20: return 4
    if multiple >= 5: return 3
    if multiple >= 1: return 2
    return 1 if units else 0


# Probability reserved for worthwhile bands before the 96% calibrator runs.
# Units are hundredths of the ordinary bet. Tail books stay outside these bands.
FEEL_BANDS = {
    1: (
        (40, 200, 0.30),
        (200, 800, 0.09),
        (800, 5000, 0.028),
        (5000, 30000, 0.0035),
    ),
    100: (
        (6000, 14000, 0.48),
        (14000, 25000, 0.18),
        (25000, 40000, 0.05),
    ),
}


def release_weights(books, cost):
    """Keep the 10,000× cap rare and put most return into frequent mid-size wins."""
    scale = 1_000_000_000_000
    bands = FEEL_BANDS[int(cost)]
    feel = 1.0
    last_error = None
    for _ in range(8):
        try:
            return _weights_for_feel(books, cost, scale, bands, feel)
        except ValueError as error:
            last_error = error
            feel *= 0.82
    raise ValueError(f'Could not place mid-win weight at 96% RTP: {last_error}')


# 10,000× is reserved across every cap book so the combined rate is 1 in 10,000,000 rounds.
MAX_WIN_ODDS = 5_000_000


def _weights_for_feel(books, cost, scale, bands, feel):
    """Hold 96% and the 10,000× rate. Tilt toward mid-size wins without isolating them."""
    cap_books = [index for index, book in enumerate(books) if book['payoutMultiplier'] == MAX_UNITS]
    if not cap_books:
        raise ValueError('10,000× book is missing')
    cap_set = set(cap_books)
    reserved = {}
    for index, book in enumerate(books):
        if index not in cap_set and book['criteria'] == 'tail':
            reserved[index] = 1_000
    ordinary_index = [index for index in range(len(books)) if index not in reserved and index not in cap_set]
    ordinary = [books[index] for index in ordinary_index]
    remainder = scale - sum(reserved.values())
    if remainder < len(ordinary) or not ordinary:
        raise ValueError('No ordinary books left to calibrate')
    planned = sum(reserved.values()) + remainder
    cap_mass = max(len(cap_books), round(planned / (MAX_WIN_ODDS - 1)))
    reserved_payout = sum(books[index]['payoutMultiplier'] * weight for index, weight in reserved.items())
    ordinary_payout = 0.96 * 100 * cost * (planned + cap_mass) - reserved_payout - MAX_UNITS * cap_mass
    target = ordinary_payout / (100 * cost * remainder)
    # A light log tilt keeps more weight on 0.4×–50× books when the pool allows it.
    tilted = []
    for index in ordinary_index:
        payout = books[index]['payoutMultiplier']
        bonus = 0
        for lower, upper, probability in bands:
            if lower <= payout <= upper:
                bonus = probability * feel
                break
        tilted.append({**books[index], 'payoutMultiplier': payout, '_tilt': bonus})
    ordinary_returns = [book['payoutMultiplier'] / (100 * cost) for book in ordinary]
    if not 0 < target < 1 or not min(ordinary_returns) <= target <= max(ordinary_returns):
        raise ValueError(f'Ordinary target {target:.4f} is outside the generated books')
    normal, _ = calibrate(ordinary, cost, target=target, weight_scale=remainder)
    if feel > 0:
        # Reallocate a slice of ordinary weight toward the feel bands, then repair RTP.
        band_members = [index for index in ordinary_index if any(
            lower <= books[index]['payoutMultiplier'] <= upper for lower, upper, _ in bands)]
        if band_members and len(band_members) < len(ordinary_index):
            move = int(remainder * 0.08 * feel)
            donors = [index for index in ordinary_index if index not in band_members]
            if donors and move > len(donors):
                per_take = move // len(donors)
                per_give = move // len(band_members)
                adjusted = {index: weight for index, weight in zip(ordinary_index, normal)}
                for index in donors:
                    adjusted[index] = max(1, adjusted[index] - per_take)
                for index in band_members:
                    adjusted[index] += per_give
                trial = [adjusted[index] for index in ordinary_index]
                if abs(weighted_rtp(ordinary, trial, cost) - target) <= 1e-6:
                    normal = trial
    iterator = iter(normal)
    weights = []
    for index in range(len(books)):
        if index in cap_set:
            weights.append(0)
        elif index in reserved:
            weights.append(reserved[index])
        else:
            weights.append(next(iterator))
    others = sum(weights)
    cap_mass = max(len(cap_books), round(others / (MAX_WIN_ODDS - 1)))
    share, extra = divmod(cap_mass, len(cap_books))
    if share < 1:
        raise ValueError('Cap weight vanished')
    for offset, index in enumerate(cap_books):
        weights[index] = share + (1 if offset < extra else 0)
    actual = weighted_rtp(books, weights, cost)
    if abs(actual - 0.96) > 1e-6:
        raise ValueError(f'Calibration missed 96%: {actual}')
    total = sum(weights)
    worthwhile = sum(weight for book, weight in zip(books, weights) if book['payoutMultiplier'] >= 40)
    if cost == 1 and worthwhile / total < 0.28:
        raise ValueError('Base game would not hit often enough above 0.4×')
    cap_probability = sum(weights[index] for index in cap_books) / total
    if abs(cap_probability - 1 / MAX_WIN_ODDS) > 1e-9:
        raise ValueError(f'Cap rate {cap_probability:.12g} is not 1 in {MAX_WIN_ODDS:,}')
    return weights


def feel_summary(books, weights, cost):
    total = sum(weights)
    ordered = sorted(zip((book['payoutMultiplier'] for book in books), weights))
    running = 0
    median = ordered[-1][0]
    for payout, weight in ordered:
        running += weight
        if running * 2 >= total:
            median = payout
            break

    def band(lower, upper):
        return sum(weight for book, weight in zip(books, weights)
                   if lower <= book['payoutMultiplier'] <= upper) / total

    hit = sum(weight for book, weight in zip(books, weights) if book['payoutMultiplier'] > 0) / total
    return (f"median {median / 100:.2f}x cost-relative {median / (100 * cost):.2f}x; "
            f"hit {hit:.2%}; 0.4-2x {band(40, 200):.2%}; 2-8x {band(200, 800):.2%}; "
            f"8-50x {band(800, 5000):.2%}; 50-300x {band(5000, 30000):.2%}; "
            f"5000-10000x {band(500000, MAX_UNITS):.6%}")


def write_lut(path, books, weights):
    with open(path, 'w', newline='') as f:
        csv.writer(f).writerows((b['id'],w,b['payoutMultiplier']) for b,w in zip(books, weights))


def main():
    global OUT, DIST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frontend-only', action='store_true')
    parser.add_argument('--release', action='store_true')
    args = parser.parse_args()
    if args.frontend_only:
        copy_frontend(); print('Frontend copied; math preserved'); return
    if args.release:
        OUT = os.path.join(ROOT, 'release/math')
        DIST = os.path.join(ROOT, 'release/frontend')
    Path(OUT).mkdir(parents=True, exist_ok=True)
    Path(DIST).mkdir(parents=True, exist_ok=True)
    random.seed(int(os.environ.get('VICE_HEIST_SEED', '1988')))
    builder = BookBuilder()
    config = {'gameName': 'Vice Heist', 'maxWin': 10000, 'paylines': 20,
              'payoutUnit': '100 = 1.0x ordinary bet', 'sdkRevision': SDK_REVISION,
              'requiresRGS': args.release, 'betLevels': BET_MICROS,
              'paytable': {s.value: p for s,p in Paytable.SYMBOL_PAYS.items()}, 'paylinePaths': Paytable.PAYLINES, 'modes': {}}
    replay = {}
    for mode,cost,default in [('base',1,4000), ('bonus',100,1200)]:
        n = int(os.environ.get('VICE_HEIST_'+mode.upper(), '100000' if args.release else str(default)))
        if n < (100000 if args.release else len(TAILS)+10): raise ValueError('Insufficient outcome count')
        books = []
        preview = []
        path = Path(OUT, f'books_{mode}.jsonl.zst')
        with path.open('wb') as f, zstd.ZstdCompressor(level=10).stream_writer(f) as stream:
            for i in range(n):
                book = builder.build_round(i+1, mode, TAILS[i] if i<len(TAILS) else None)
                stream.write((json.dumps(book,separators=(',',':'))+'\n').encode())
                books.append({k: book[k] for k in ('id','payoutMultiplier','criteria')})
                if not args.release: preview.append({'id':book['id'], 'payoutMultiplier':book['payoutMultiplier'], 'events':book['events']})
                if i and i%10000==0: print(f'{mode}: {i:,}/{n:,} books',flush=True)
        weights = release_weights(books,cost)
        write_lut(Path(OUT,f'lookUpTable_{mode}.csv'),books,weights)
        if not args.release:
            Path(DIST,f'books_{mode}.json').write_text(json.dumps(preview,separators=(',',':')))
            write_lut(Path(DIST,f'lookUpTable_{mode}.csv'),books,weights)
            # Preserve optional uncompressed diagnostic files for existing tools.
            with Path(OUT,f'books_{mode}.jsonl').open('w') as f:
                for book in preview: f.write(json.dumps(book,separators=(',',':'))+'\n')
        rtp = weighted_rtp(books, weights,cost)
        maximum = max(b['payoutMultiplier'] for b in books)
        cap_probability = sum(w for b,w in zip(books,weights) if b['payoutMultiplier']==MAX_UNITS)/sum(weights)
        config['modes'][mode] = {'cost':cost, 'rtp':rtp, 'maxWin':maximum/100, 'books':n,
             'maxWinProbability':cap_probability, 'effectiveBooks':effective_book_count(weights)}
        replay[mode] = {kind: next(b['id'] for b in books if b['criteria']==kind) for kind in ['loss','maxwin','tail']}
        replay[mode]['win'] = next(b['id'] for b in books if 0<b['payoutMultiplier']<1000)
        replay[mode]['bonusTrigger'] = next(b['id'] for b in books if b['criteria']=='freegame')
        odds = 1 / cap_probability if cap_probability else float('inf')
        print(f'{mode}: {n:,} books; RTP {rtp:.8%}; 10,000× about 1 in {odds:,.0f}; {feel_summary(books, weights, cost)}', flush=True)
    config['rtpBase'] = config['modes']['base']['rtp']*100
    config['rtpBonus'] = config['modes']['bonus']['rtp']*100
    Path(OUT,'index.json').write_text(json.dumps({'modes':[{'name':m,'cost':c,'events':f'books_{m}.jsonl.zst','weights':f'lookUpTable_{m}.csv'} for m,c in [('base',1.0),('bonus',100.0)]]},indent=2))
    Path(OUT,'math_summary.json').write_text(json.dumps(config,indent=2))
    Path(OUT,'replay_ids.json').write_text(json.dumps(replay,indent=2))
    Path(DIST,'game_config.json').write_text(json.dumps(config,indent=2))
    copy_frontend()
    if args.release:
        # No selectable local outcomes or demo balance in the production build.
        for pattern in ('books_*.json','lookUpTable_*.csv'):
            for file in Path(DIST).glob(pattern): file.unlink()
    print(f'Math: {OUT}; frontend: {DIST}',flush=True)


if __name__ == '__main__': main()
