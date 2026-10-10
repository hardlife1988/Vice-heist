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


def copy_frontend():
    names = ('index.html', 'style.css', 'game.js', 'money.js', 'rgs.js')
    # The original packaging tests provide the three legacy mandatory files.
    required = names[:3]
    missing = [os.path.join(STATIC, n) for n in required if not Path(STATIC, n).is_file()]
    if not Path(STATIC, 'assets').is_dir(): missing.append(os.path.join(STATIC, 'assets'))
    if missing: raise FileNotFoundError('Missing frontend inputs: '+', '.join(missing))
    Path(DIST).mkdir(parents=True, exist_ok=True)
    for n in names:
        if Path(STATIC, n).exists(): shutil.copyfile(Path(STATIC, n), Path(DIST, n))
    shutil.copytree(Path(STATIC, 'assets'), Path(DIST, 'assets'), dirs_exist_ok=True)


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
            events.append({'index': len(events), 'type': 'setWin', 'amount': spin, 'winLevel': 1 if spin < 500 else 2})
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
            positions = [{'reel': r, 'row': row} for row in range(3) for r in range(5) if grid[row][r] == Symbol.SCATTER]
        if feature and self.total < MAX_UNITS:
            events.append({'index': len(events), 'type': 'freeSpinTrigger', 'totalFs': 10, 'positions': positions})
            if mode == 'bonus': events.append({'index': len(events), 'type': 'enterBonus', 'reason': 'bonusBuy'})
            for i in range(10):
                events.append({'index': len(events), 'type': 'updateFreeSpin', 'amount': i+1, 'total': 10})
                _, _, spin = self._spin(events, 'bonus_buy' if mode == 'bonus' else 'natural_bonus', 2, i)
                free += spin
                if self.total == MAX_UNITS: break
            events.append({'index': len(events), 'type': 'freeSpinEnd', 'amount': free, 'winLevel': 2})
        events.append({'index': len(events), 'type': 'finalWin', 'amount': self.total})
        assert base+free == self.total and self.total % 10 == 0
        return {'id': book_id, 'payoutMultiplier': self.total, 'events': events,
                'criteria': scenario[0] if scenario else 'freegame' if feature else 'basegame',
                'baseGameWins': base/100, 'freeGameWins': free/100}


def release_weights(books, cost):
    # Explicit rare, legal boards keep the advertised cap attainable. Their
    # weights are probabilities in the published static game, not reel RNG odds.
    special = [i for i,b in enumerate(books) if b['criteria'] in ('maxwin', 'tail')]
    scale = 1_000_000_000_000
    reserved = {i: 1_000_000 if books[i]['criteria']=='maxwin' else 100_000 for i in special}
    ordinary = [b for i,b in enumerate(books) if i not in reserved]
    remainder = scale-sum(reserved.values())
    target = (0.96*cost*100*scale-sum(books[i]['payoutMultiplier']*w for i,w in reserved.items()))/(100*cost*remainder)
    normal, _ = calibrate(ordinary, cost, target=target, weight_scale=remainder)
    it = iter(normal)
    weights = [reserved[i] if i in reserved else next(it) for i in range(len(books))]
    actual = weighted_rtp(books, weights, cost)
    if abs(actual-.96)>1e-6: raise ValueError(f'Calibration missed 96%: {actual}')
    return weights


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
        print(f'{mode}: {n:,} books; RTP {rtp:.8%}; cap probability {cap_probability:.8g}', flush=True)
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
