const { test } = require('node:test');
const assert = require('node:assert/strict');
const api = require('../game.js');

function assertMoney(value, expected) {
  assert.equal(Math.round(Number(value) * 100) / 100, expected);
}

test('multiplier × bet crediting is calculated in cents and capped correctly', () => {
  const bet = 2.5;
  const multiplier = 3.75;
  const credit = api.decodeWinCents(multiplier, bet);
  const expected = Math.round((multiplier * bet) * 100);
  assert.equal(credit, expected);
  assert.equal(api.centsToCash(credit), (multiplier * bet));
});

test('base mode credits 1.5× bet for a $2.00 wager', () => {
  const bet = 2.0;
  const credit = api.decodeWinCents(1.5, bet);
  assert.equal(credit, 300);
  assertMoney(api.centsToCash(credit), 3.0);
});

test('bonus buy cost is 100× the base bet', () => {
  const bonusCost = api.EngineClient.bonusBuyCost(2.5);
  assert.equal(bonusCost, 250);
});

test('cap prevents payouts above 10,000× the bet', () => {
  const bet = 5;
  const hugeMultiplier = 25000;
  const credit = api.decodeWinCents(hugeMultiplier, bet);
  const cap = api.toCents(bet * api.CONFIG.maxWinMultiplier);
  assert.equal(credit, cap);
  assert.ok(credit <= cap);
});

test('zero and invalid multipliers safely return zero', () => {
  assert.equal(api.decodeWinCents(0, 5), 0);
  assert.equal(api.decodeWinCents(undefined, 5), 0);
  assert.equal(api.decodeWinCents('bad', 5), 0);
  assert.equal(api.decodeWinCents(3, undefined), 0);
});

test('negative bet or multiplier is treated as zero or guarded', () => {
  assert.equal(api.decodeWinCents(-2, 10), 0);
  assert.equal(api.decodeWinCents(2, -10), 0);
});

test('ladder rounding preserves integer-cent precision', () => {
  const bet = 0.25;
  const multiplier = 7.625;
  const credit = api.decodeWinCents(multiplier, bet);
  const expected = Math.round((7.625 * 0.25) * 100);
  assert.equal(credit, expected);
  assert.equal(api.centsToCash(credit), 1.90625);
});

test('centsToCash converts micro-units back to decimal currency correctly', () => {
  assert.equal(api.centsToCash(1234), 12.34);
  assert.equal(api.centsToCash(0), 0);
  assert.equal(api.centsToCash(-50), -0.5);
});

test('toCents converts a decimal float to integer cents', () => {
  assert.equal(api.toCents(1.234), 123);
  assert.equal(api.toCents(0.005), 1);
  assert.equal(api.toCents(2.999), 300);
});

test('Game export remains stable and includes requested members', () => {
  assert.ok(api.Game);
  assert.ok(api.EngineClient);
  assert.ok(api.CONFIG);
  assert.equal(typeof api.centsToCash, 'function');
  assert.equal(typeof api.toCents, 'function');
  assert.equal(typeof api.decodeWinCents, 'function');
});

test('bonus buy limits are not allowed to exceed max win cap', () => {
  const bet = 100;
  const buyCost = api.EngineClient.bonusBuyCost(bet);
  assert.equal(buyCost, 10000);
  const win = api.decodeWinCents(10000, bet);
  assert.ok(win <= api.toCents(bet * api.CONFIG.maxWinMultiplier));
});

test('guard for non-finite numeric input returns zero', () => {
  assert.equal(api.decodeWinCents(Number.NaN, 5), 0);
  assert.equal(api.decodeWinCents(5, Number.POSITIVE_INFINITY), 0);
  assert.equal(api.decodeWinCents(Number.NEGATIVE_INFINITY, 5), 0);
});
