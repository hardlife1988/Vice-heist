(function (global) {
  const CONFIG = {
    game: 'Vice Heist',
    maxWinMultiplier: 10000,
    bonusBuyMultiplier: 100,
    modes: ['base', 'bonus'],
    currency: 'USD',
    mathFileFormat: {
      baseLut: 'lookUpTable_base.csv',
      bonusLut: 'lookUpTable_bonus.csv',
      baseBooks: 'books_base.json',
      bonusBooks: 'books_bonus.json'
    }
  };

  function toCents(value) {
    const numeric = Number(value ?? 0);
    if (!Number.isFinite(numeric)) return 0;
    return Math.round(numeric * 100);
  }

  function centsToCash(cents) {
    const numeric = Number(cents ?? 0);
    if (!Number.isFinite(numeric)) return 0;
    return Math.round(numeric) / 100;
  }

  function decodeWinCents(multiplier, bet) {
    const winMultiplier = Number(multiplier ?? 0);
    const betValue = Number(bet ?? 0);
    if (!Number.isFinite(winMultiplier) || !Number.isFinite(betValue)) {
      return 0;
    }
    const rawCents = winMultiplier * toCents(betValue);
    const capCents = toCents(betValue * CONFIG.maxWinMultiplier);
    return Math.min(Math.round(rawCents), capCents);
  }

  const Game = {
    id: 'vice-heist',
    name: 'Vice Heist',
    CONFIG,
    maxWinMultiplier: CONFIG.maxWinMultiplier,
    decodeWinCents,
    creditMultiplier(multiplier, bet) {
      return decodeWinCents(multiplier, bet);
    }
  };

  const EngineClient = {
    bonusBuyCost(bet) {
      return Math.round((Number(bet ?? 0) || 0) * CONFIG.bonusBuyMultiplier);
    },
    computeWinCents(multiplier, bet) {
      return decodeWinCents(multiplier, bet);
    },
    payoutFromWinCents(cents) {
      return centsToCash(cents);
    }
  };

  const api = {
    Game,
    EngineClient,
    CONFIG,
    centsToCash,
    toCents,
    decodeWinCents
  };

  global.ViceHeist = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
