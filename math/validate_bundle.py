"""Exhaustive event, evaluator, weight and payout audit of generated books."""
import argparse,csv,io,json
from pathlib import Path
from decimal import Decimal
import zstandard
from build_stake_bundle import MAX_UNITS,to_cents
from game_config import GameConfig
from paytable import Symbol,Paytable
from win_evaluator import WinEvaluator
ROOT=Path(__file__).resolve().parent.parent

def validate_event_sequence(book, mode):
    """Verify the feature lifecycle, not just payouts.

    Free spins start at 10 and 2×. A winning free spin raises the next multiplier
    by 1, up to 5×. Every 3 scatters anywhere adds 3 spins, up to 30 total.
    There is no expanding symbol. A 10,000× cap may end the feature early.
    """
    assert mode in ('base', 'bonus')
    events = book['events']
    config = GameConfig()
    cursor = 0
    total = 0

    def take(kind):
        nonlocal cursor
        assert cursor < len(events), f"Missing {kind} event"
        event = events[cursor]
        assert event['index'] == cursor and event['type'] == kind, (
            f"Expected {kind} at event {cursor}"
        )
        cursor += 1
        return event

    def spin(game_type):
        nonlocal total
        reveal = take('reveal')
        assert reveal['gameType'] == game_type
        board = reveal['board']
        assert len(board) == config.reels and all(len(col) == config.rows for col in board)
        previous = total
        has_win = cursor < len(events) and events[cursor]['type'] == 'winInfo'
        if has_win:
            take('winInfo')
            take('setWin')
        total = take('setTotalWin')['amount']
        assert isinstance(total, int) and previous <= total <= MAX_UNITS
        assert has_win == (total > previous)
        if total == MAX_UNITS:
            assert take('wincap')['amount'] == MAX_UNITS
        return board

    positions = []
    feature = mode == 'bonus'
    if mode == 'base':
        board = spin('basegame')
        positions = [
            {'reel': reel, 'row': row}
            for row in range(config.rows) for reel in range(config.reels)
            if board[reel][row]['name'] == Symbol.SCATTER.value
        ]
        feature = len(positions) >= config.free_spins_trigger
    if feature and total < MAX_UNITS:
        trigger = take('freeSpinTrigger')
        assert trigger['totalFs'] == config.free_spins_count
        assert trigger['positions'] == positions
        assert trigger['multiplier'] == config.free_spins_multiplier
        if mode == 'bonus':
            assert take('enterBonus')['reason'] == 'bonusBuy'
        base_total = total
        awarded = config.free_spins_count
        expected_mult = config.free_spins_multiplier
        number = 0
        while number < awarded:
            number += 1
            update = take('updateFreeSpin')
            assert update['amount'] == number and update['total'] == awarded
            assert update['multiplier'] == expected_mult
            assert take('setMultiplier')['amount'] == expected_mult
            before = total
            board = spin('freegame')
            if total == MAX_UNITS:
                break
            if total > before and expected_mult < config.free_spins_multiplier_cap:
                expected_mult += 1
            scatters = sum(cell['name'] == Symbol.SCATTER.value for column in board for cell in column)
            room = config.free_spins_max - awarded
            extra_spins = 0 if room <= 0 or scatters < config.free_spins_trigger else min(
                (scatters // config.free_spins_trigger) * config.free_spins_retrigger, room)
            if extra_spins:
                extra = take('freeSpinRetrigger')
                assert extra['extra'] == extra_spins
                awarded += extra['extra']
                assert extra['totalFs'] == awarded <= config.free_spins_max
            elif cursor < len(events) and events[cursor]['type'] == 'freeSpinRetrigger':
                raise AssertionError('Retrigger does not match the board')
        assert take('freeSpinEnd')['amount'] == total - base_total
    assert take('finalWin')['amount'] == total == book['payoutMultiplier']
    assert cursor == len(events), 'Events remain after finalWin'

def audit(directory,mode,cost,release=False):
    with (directory/f'lookUpTable_{mode}.csv').open(newline='') as lookup:
        rows=[tuple(map(int,r)) for r in csv.reader(lookup)]
    assert len(rows)>= (100000 if release else 1)
    assert all(i==j+1 and 0<w<2**64 and p%10==0 and 0<=p<=MAX_UNITS for j,(i,w,p) in enumerate(rows))
    total_weight=sum(w for _,w,_ in rows);assert total_weight<2**64
    evaluator=WinEvaluator(GameConfig());count=0
    with (directory/f'books_{mode}.jsonl.zst').open('rb') as compressed, zstandard.ZstdDecompressor().stream_reader(compressed) as stream:
      for line in io.TextIOWrapper(stream):
        b=json.loads(line);i,w,p=rows[count];assert (b['id'],b['payoutMultiplier'])==(i,p)
        validate_event_sequence(b, mode)
        total=0;spin=None;free=0;is_free=False;finals=0;raw=[];remaining=MAX_UNITS;pending_mult=1
        for index,e in enumerate(b['events']):
          assert e['index']==index
          kind=e['type']
          if kind=='setMultiplier':
            pending_mult=e['amount']
          elif kind=='reveal':
            if spin is not None: assert spin==0
            board=e['board'];assert len(board)==5 and all(len(c)==3 for c in board)
            grid=[[Symbol(board[r][y]['name']) for r in range(5)] for y in range(3)]
            is_free=e['gameType']=='freegame'
            result=evaluator.evaluate_spin(grid,1.0,pending_mult if is_free else 1)
            pending_mult=1
            raw=[];remaining=MAX_UNITS-total
            for linewin in result['payline_wins']:
              value=min(to_cents(linewin['win']),remaining)
              if value:
                positions=[{'reel':r,'row':Paytable.PAYLINES[linewin['payline']][r]} for r in range(linewin['count'])]
                raw.append((linewin['symbol_key'],linewin['count'],value,positions));remaining-=value
            value=min(to_cents(result['scatter_win']),remaining)
            if value:raw.append(('S',result['scatter_count'],value,[]))
            spin=sum(x[2] for x in raw)
          elif kind=='winInfo':
            assert [(x['symbol'],x['kind'],x['win'],x['positions']) for x in e['wins']]==raw
            assert e['totalWin']==spin
          elif kind=='setWin':
            assert e['amount']==spin
          elif kind=='setTotalWin':
            assert spin is not None
            total+=spin
            if is_free:free+=spin
            assert e['amount']==total
            spin=0
          elif kind=='wincap': assert total==MAX_UNITS and e['amount']==MAX_UNITS
          elif kind=='freeSpinEnd': assert e['amount']==free
          elif kind=='finalWin':finals+=1;assert e['amount']==total==p
          elif kind not in ('freeSpinTrigger','enterBonus','updateFreeSpin','freeSpinRetrigger','setMultiplier'):raise ValueError('Unknown event '+kind)
        assert finals==1
        count+=1
    assert count==len(rows)
    rtp=sum(w*p for _,w,p in rows)/(total_weight*100*cost)
    cap=sum(w for _,w,p in rows if p==MAX_UNITS)/total_weight
    hit=sum(w for _,w,p in rows if p>0)/total_weight
    assert abs(rtp-.96)<1e-6 and max(p for _,_,p in rows)==MAX_UNITS
    if release:
        assert abs(cap - 2e-7) < 1e-9 and hit >= .05
    else:
        assert cap > 0
    return dict(mode=mode,books=count,rtp=rtp,cap_probability=cap,win_probability=hit,all_events_verified=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--publish',type=Path,default=ROOT/'math/library/publish_files');parser.add_argument('--release',action='store_true');a=parser.parse_args()
    results=[audit(a.publish,m,c,a.release) for m,c in [('base',1),('bonus',100)]]
    assert abs(results[0]['rtp']-results[1]['rtp'])<=.005
    (a.publish/'validation_report.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
