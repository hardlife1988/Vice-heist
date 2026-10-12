"""Regression checks for payout-correct books with broken feature events."""
import copy
import csv
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

import zstandard

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'math'))
from build_stake_bundle import BookBuilder, TAILS
from validate_bundle import audit, validate_event_sequence


def reindex(book):
    for index, event in enumerate(book['events']):
        event['index'] = index


class EventContractTests(unittest.TestCase):
    def setUp(self):
        self.builder = BookBuilder()
        self.base = self.builder.build_round(1, 'base', ('tail', 0, 1))
        self.bonus = self.builder.build_round(1, 'bonus', ('loss', 0, 0))

    def reject(self, book, mode='base'):
        reindex(book)
        with self.assertRaises(AssertionError):
            validate_event_sequence(book, mode)

    def test_generated_rounds_and_cap_early_termination_are_valid(self):
        state = random.getstate()
        try:
            random.seed(1988)
            for mode in ('base', 'bonus'):
                for scenario in TAILS + [None] * 50:
                    with self.subTest(mode=mode, scenario=scenario):
                        validate_event_sequence(self.builder.build_round(1, mode, scenario), mode)
        finally:
            random.setstate(state)

    def test_wrong_trigger_count_or_positions(self):
        for field, value in [('totalFs', 999), ('positions', [])]:
            book = copy.deepcopy(self.base)
            next(e for e in book['events'] if e['type'] == 'freeSpinTrigger')[field] = value
            self.reject(book)

    def test_wrong_free_spin_counter_or_total(self):
        for field in ('amount', 'total'):
            book = copy.deepcopy(self.base)
            next(e for e in book['events'] if e['type'] == 'updateFreeSpin')[field] = 999
            self.reject(book)

    def test_missing_feature_events(self):
        for kind in ('freeSpinTrigger', 'updateFreeSpin', 'freeSpinEnd'):
            book = copy.deepcopy(self.base)
            event = next(e for e in book['events'] if e['type'] == kind)
            book['events'].remove(event)
            self.reject(book)

    def test_missing_final_zero_win_free_spin(self):
        book = copy.deepcopy(self.base)
        start = next(i for i, e in enumerate(book['events'])
                     if e['type'] == 'updateFreeSpin' and e['amount'] == 10)
        end = next(i for i, e in enumerate(book['events']) if e['type'] == 'freeSpinEnd')
        del book['events'][start:end]
        self.reject(book)

    def test_mode_and_game_type_must_match(self):
        self.reject(copy.deepcopy(self.base), 'bonus')
        self.reject(copy.deepcopy(self.bonus), 'base')
        book = copy.deepcopy(self.base)
        next(e for e in book['events'] if e['type'] == 'reveal')['gameType'] = 'unknown'
        self.reject(book)

    def test_bonus_buy_entry_contract(self):
        book = copy.deepcopy(self.bonus)
        next(e for e in book['events'] if e['type'] == 'enterBonus')['reason'] = 'unknown'
        self.reject(book, 'bonus')
        book = copy.deepcopy(self.bonus)
        book['events'] = [e for e in book['events'] if e['type'] != 'enterBonus']
        self.reject(book, 'bonus')

    def test_final_win_must_be_terminal(self):
        book = copy.deepcopy(self.base)
        book['events'].append({'type': 'updateFreeSpin', 'amount': 11, 'total': 10})
        self.reject(book)

    def test_missing_cap_event_is_rejected(self):
        book = self.builder.build_round(1, 'base', ('maxwin', 10, 0))
        book['events'] = [e for e in book['events'] if e['type'] != 'wincap']
        self.reject(book)

    def test_full_audit_rejects_malformed_feature_with_valid_rtp_and_payouts(self):
        state = random.getstate()
        try:
            random.seed(1988)
            while True:
                ordinary = self.builder.build_round(2, 'base')
                if ordinary['payoutMultiplier'] == 10:
                    break
        finally:
            random.setstate(state)
        books = [self.builder.build_round(1, 'base', ('loss', 0, 0)), ordinary,
                 self.builder.build_round(3, 'base', ('maxwin', 10, 0))]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with (path / 'lookUpTable_base.csv').open('w', newline='') as file:
                csv.writer(file).writerows([(1, 4999090, 0), (2, 5000000, 10), (3, 910, 1000000)])

            def write_books():
                data = ''.join(json.dumps(b) + '\n' for b in books).encode()
                (path / 'books_base.jsonl.zst').write_bytes(zstandard.ZstdCompressor().compress(data))

            write_books()
            self.assertEqual(audit(path, 'base', 1)['rtp'], 0.96)
            next(e for e in books[2]['events'] if e['type'] == 'freeSpinTrigger')['totalFs'] = 999
            write_books()
            with self.assertRaises(AssertionError):
                audit(path, 'base', 1)


if __name__ == '__main__':
    unittest.main()
