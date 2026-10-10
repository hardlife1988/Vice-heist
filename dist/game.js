/* Vice Heist — Stake book player (static, no Flask) */
'use strict';

const SYMBOL_EMOJI = {
  W: '🃏', S: '📖', B: '📚', G: '🪙',
  D: '💎', R: '🔴', E: '💚', C: '♣', P: '♠', H: '♥',
};
const SYMBOL_ASSETS = {
  "W": "assets/symbols/wild.webp",
  "S": "assets/symbols/scatter.webp",
  "B": "assets/symbols/open_safe.webp",
  "G": "assets/symbols/gold_bars.webp",
  "D": "assets/symbols/diamond.webp",
  "R": "assets/symbols/pink_gem.webp",
  "E": "assets/symbols/cash.webp",
  "C": "assets/symbols/king.webp",
  "P": "assets/symbols/ace.webp",
  "H": "assets/symbols/queen.webp"
};
const SYMBOL_NAME = {
  W: 'Wild', S: 'Scatter', B: 'Book', G: 'Gold',
  D: 'Diamond', R: 'Ruby', E: 'Emerald', C: 'Club', P: 'Spade', H: 'Heart',
};

let math = {
  baseBooks: [],
  bonusBooks: [],
  baseLut: [],
  bonusLut: [],
  config: { rtpBase: 96, maxWin: 10000 },
};

let state = {
  balance: 1000,
  bet: 1,
  spinning: false,
  ready: false,
  turbo: false,
  lastWin: 0,
  muted: false,
};

const BET_PRESETS = [0.20, 0.40, 1.00, 2.00, 5.00, 10.00, 20.00, 50.00, 100.00];

const $ = (id) => document.getElementById(id);
const $balance = $('balance');
const $totalWin = $('total-win');
const $betValue = $('bet-value');
const $bonusCost = $('bonus-cost');
const $reelsGrid = $('reels-grid');
const $winBanner = $('win-banner');
const $winBannerText = $('win-banner-text');
const $freeSpinsBar = $('free-spins-bar');
const $fsCount = $('fs-count');
const $winLog = $('win-log');
const $btnSpin = $('btn-spin');
const $btnBetDown = $('bet-down');
const $btnBetUp = $('bet-up');
const $btnBonusBuy = $('btn-bonus-buy');
const $btnDeposit = $('btn-deposit');
const $btnMute = $('btn-mute');
const $btnTurbo = $('btn-turbo');
const $btnMenu = $('btn-menu');
const $infoPanel = $('info-panel');
const $spinText = $btnSpin.querySelector('.spin-text');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

const SAMPLE_PATHS = {
  reelStop: 'assets/audio/reel_stop.wav',
  scatter: 'assets/audio/scatter.wav',
  bonus: 'assets/audio/bonus.wav',
  win: 'assets/audio/win.wav',
  click: 'assets/audio/reel_stop.wav'
};
const SAMPLE_AUDIO = {};
const activeSamples = new Set();
function playSample(name, fallback) {
  if (state.muted || !SAMPLE_PATHS[name]) return false;
  try {
    const sample = SAMPLE_AUDIO[name] || (SAMPLE_AUDIO[name] = new Audio(SAMPLE_PATHS[name]));
    const voice = sample.cloneNode();
    voice.volume = name === 'click' ? 0.12 : 0.42;
    activeSamples.add(voice);
    const release = () => activeSamples.delete(voice);
    voice.addEventListener('ended', release, { once: true });
    voice.addEventListener('error', release, { once: true });
    voice.play().catch(() => {
      release();
      if (!state.muted) fallback();
    });
    return true;
  } catch (_) { return false; }
}
const AudioFX = {
  ctx: null, output: null,
  unlock() {
    if (state.muted) return;
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
      this.output = this.ctx.createGain();
      this.output.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') this.ctx.resume().catch(() => {});
  },
  beep(freq, dur, type, gain, when) {
    if (state.muted || !this.ctx) return;
    const t = this.ctx.currentTime + (when || 0);
    const o = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    o.type = type || 'square';
    o.frequency.setValueAtTime(freq, t);
    g.gain.setValueAtTime(gain || 0.05, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(this.output);
    o.start(t); o.stop(t + dur);
  },
  sample(name, fallback) {
    this.unlock();
    if (!playSample(name, fallback)) fallback();
  },
  mute(on) {
    if (this.output) this.output.gain.setValueAtTime(on ? 0 : 1, this.ctx.currentTime);
    if (on) {
      activeSamples.forEach(voice => { voice.pause(); voice.currentTime = 0; });
      activeSamples.clear();
    } else this.unlock();
  },
  click() { this.sample('click', () => this.beep(420, 0.05, 'square', 0.04)); },
  reelStop() { this.sample('reelStop', () => this.beep(180, 0.08, 'triangle', 0.07)); },
  scatter() { this.sample('scatter', () => { this.beep(880, 0.18, 'sine', 0.06); this.beep(1320, 0.22, 'sine', 0.04, 0.08); }); },
  win(amount, bet) {
    this.sample('win', () => {
      this.beep(520, 0.12, 'triangle', 0.06);
      this.beep(780, 0.16, 'triangle', 0.05, 0.08);
      if (amount >= bet * 5) this.beep(1040, 0.28, 'sawtooth', 0.04, 0.16);
    });
  },
  bonus() {
    this.sample('bonus', () => {
      [523, 659, 784, 1046].forEach((f, i) => this.beep(f, 0.2, 'triangle', 0.05, i * 0.09));
    });
  },
};

function sleep(ms) {
  return new Promise(r => setTimeout(r, reducedMotion.matches ? 0 : state.turbo ? ms / 4 : ms));
}
function fmt(n) { return '$' + Number(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
function centsToCash(cents) { return (cents / 100) * state.bet; }

function parseLut(text) {
  if (!text.trim()) throw new Error('Empty lookup table');
  return text.trim().split(/\n+/).map(line => {
    if (line.split(',').length !== 3) throw new Error('Invalid lookup table');
    const [id, weight, payout] = line.split(',').map(Number);
    if (![id, weight, payout].every(Number.isSafeInteger) || id <= 0 || weight <= 0 || payout < 0) {
      throw new Error('Invalid lookup table');
    }
    return { id, weight, payout };
  });
}

function validateMode(lut, books) {
  if (!Array.isArray(books) || !books.length) throw new Error('Empty game books');
  const byId = new Map();
  for (const book of books) {
    if (!Number.isSafeInteger(book.id) || book.id <= 0 || byId.has(book.id) ||
        !Number.isSafeInteger(book.payoutMultiplier) || book.payoutMultiplier < 0 ||
        !Array.isArray(book.events) || !book.events.length) throw new Error('Invalid game book');
    const final = book.events.filter(event => event.type === 'finalWin');
    if (final.length !== 1 || final[0].amount !== book.payoutMultiplier) throw new Error('Invalid book payout');
    byId.set(book.id, book);
  }
  const seen = new Set();
  for (const row of lut) {
    if (seen.has(row.id) || !byId.has(row.id) || byId.get(row.id).payoutMultiplier !== row.payout) {
      throw new Error('Lookup table does not match game books');
    }
    seen.add(row.id);
  }
  if (seen.size !== byId.size || !Number.isSafeInteger(lut.reduce((sum, row) => sum + row.weight, 0))) {
    throw new Error('Incomplete lookup table');
  }
}

function pickWeighted(lut, books) {
  const total = lut.reduce((s, r) => s + r.weight, 0);
  let roll = Math.random() * total;
  let chosen = lut[0];
  for (const row of lut) {
    roll -= row.weight;
    if (roll <= 0) { chosen = row; break; }
  }
  return books.find(b => b.id === chosen.id);
}

function buildGrid() {
  $reelsGrid.innerHTML = '';
  for (let row = 0; row < 3; row++) {
    for (let reel = 0; reel < 5; reel++) {
      const cell = document.createElement('div');
      cell.className = 'reel-cell';
      cell.id = `cell-${row}-${reel}`;
      cell.innerHTML = '<span class="sym-ico">?</span><span class="sym-name">READY</span>';
      $reelsGrid.appendChild(cell);
    }
  }
}

function paintCell(row, reel, sym, extraClass) {
  const cell = document.getElementById(`cell-${row}-${reel}`);
  if (!cell) return;
  const code = sym && typeof sym === 'object' ? (sym.name || '?') : (sym || '?');
  cell.dataset.sym = code;
  cell.classList.remove('win-cell', 'spinning', 'landed');
  if (extraClass) cell.classList.add(extraClass);
  const imagePath = SYMBOL_ASSETS[code];
  cell.replaceChildren();
  if (imagePath) {
    const img = document.createElement('img');
    img.className = 'sym-image';
    img.src = imagePath;
    img.alt = SYMBOL_NAME[code] || code;
    img.loading = 'eager';
    img.decoding = 'async';
    img.onerror = () => {
      img.replaceWith(document.createTextNode(SYMBOL_EMOJI[code] || code));
    };
    cell.appendChild(img);
  } else {
    const icon = document.createElement('span');
    icon.className = 'sym-ico';
    icon.textContent = SYMBOL_EMOJI[code] || code;
    cell.appendChild(icon);
  }
  const name = document.createElement('span');
  name.className = 'sym-name';
  name.textContent = SYMBOL_NAME[code] || '';
  cell.appendChild(name);
}

function highlightWins(positions) {
  document.querySelectorAll('.reel-cell').forEach(c => c.classList.remove('win-cell'));
  (positions || []).forEach(p => {
    document.getElementById(`cell-${p.row}-${p.reel}`)?.classList.add('win-cell');
  });
}

function updateHUD() {
  $balance.textContent = fmt(state.balance);
  $totalWin.textContent = fmt(state.lastWin);
  $betValue.textContent = fmt(state.bet);
  $('hud-bet-value').textContent = fmt(state.bet);
  $bonusCost.textContent = fmt(state.bet * 100);
}

function showWinBanner(amount) {
  clearTimeout(showWinBanner._t);
  if (amount <= 0) { $winBanner.style.display = 'none'; $winBanner.classList.remove('big'); return; }
  const big = amount >= state.bet * 5;
  $winBannerText.textContent = (big ? 'BIG WIN  ' : 'WIN  ') + fmt(amount);
  $winBanner.classList.toggle('big', big);
  $winBanner.style.display = 'block';
  showWinBanner._t = setTimeout(() => { $winBanner.style.display = 'none'; }, 3500);
}

function setSpinning(on) {
  state.spinning = on;
  $btnSpin.disabled = on || !state.ready;
  $btnBetDown.disabled = on;
  $btnBetUp.disabled = on;
  $btnBonusBuy.disabled = on || !state.ready;
  $reelsGrid.setAttribute('aria-busy', String(on));
}

async function playReveal(event) {
  const board = event.board || [];
  if (reducedMotion.matches) {
    for (let reel = 0; reel < 5; reel++) {
      for (let row = 0; row < 3; row++) paintCell(row, reel, board[reel]?.[row], 'landed');
    }
    AudioFX.reelStop();
    return;
  }

  const spinSymbols = Object.keys(SYMBOL_ASSETS).filter(
    code => code !== 'S'
  );

  const reelStates = Array.from({ length: 5 }, (_, reel) => ({
    reel,
    running: true,
    offset: reel * 2
  }));

  /*
   * Visual animation only.
   *
   * The result has already been selected by the weighted game book.
   * These temporary symbols never affect payout or game math.
   */
  const spinTimer = setInterval(() => {
    for (const reelState of reelStates) {
      if (!reelState.running) continue;

      reelState.offset += 1;

      for (let row = 0; row < 3; row++) {
        const index =
          (reelState.offset + row) % spinSymbols.length;

        const symbol = spinSymbols[index];

        paintCell(row, reelState.reel, symbol, 'spinning');
      }
    }
  }, 70);

  /*
   * Give all five reels time to visibly accelerate before
   * the first reel stops.
   */
  try {
    await sleep(500);
    for (let reel = 0; reel < 5; reel++) {
      // Reels stop from left to right.
      await sleep(180 + reel * 35);
      reelStates[reel].running = false;
      const col = board[reel] || [];
      for (let row = 0; row < 3; row++) paintCell(row, reel, col[row], 'landed');
      AudioFX.reelStop();
    }
  } finally {
    clearInterval(spinTimer);
  }
}

async function playEvents(events) {
  for (const ev of events) {
    switch (ev.type) {
      case 'reveal':
        await playReveal(ev);
        break;
      case 'winInfo': {
        const cash = centsToCash(ev.totalWin || 0);
        const positions = (ev.wins || []).flatMap(win => win.positions || []);
        highlightWins(positions);
        $winLog.textContent = cash > 0 ? `WIN ${fmt(cash)}` : '';
        if (cash > 0) AudioFX.win(cash, state.bet);
        await sleep(280);
        break;
      }
      case 'freeSpinTrigger':
        AudioFX.scatter();
        $freeSpinsBar.style.display = 'block';
        $fsCount.textContent = ev.totalFs || 10;
        $btnSpin.classList.add('free-mode');
        $spinText.textContent = 'FREE';
        $winLog.textContent = `⚡ ${ev.totalFs || 10} FREE SPINS`;
        await sleep(450);
        break;
      case 'updateFreeSpin':
        $freeSpinsBar.style.display = 'block';
        $fsCount.textContent = `${ev.amount}/${ev.total}`;
        $spinText.textContent = 'FREE';
        await sleep(80);
        break;
      case 'enterBonus':
        AudioFX.bonus();
        $winLog.textContent = 'BONUS BUY — entering free spins';
        await sleep(300);
        break;
      case 'freeSpinEnd':
        $btnSpin.classList.remove('free-mode');
        $spinText.textContent = 'SPIN';
        $freeSpinsBar.style.display = 'none';
        break;
      case 'finalWin':
      case 'setTotalWin':
        showWinBanner(centsToCash(ev.amount || 0));
        break;
      default:
        break;
    }
  }
}

async function doPlay(mode) {
  if (state.spinning || !state.ready) return;
  AudioFX.unlock();
  const cost = mode === 'bonus' ? state.bet * 100 : state.bet;
  if (state.balance < cost) {
    $winLog.textContent = 'Insufficient demo balance — add chips below.';
    return;
  }
  const lut = mode === 'bonus' ? math.bonusLut : math.baseLut;
  const books = mode === 'bonus' ? math.bonusBooks : math.baseBooks;
  const book = pickWeighted(lut, books);
  const win = centsToCash(book.payoutMultiplier);

  setSpinning(true);
  $winLog.innerHTML = '';
  showWinBanner(0);
  state.lastWin = 0;
  state.balance = round2(state.balance - cost);
  updateHUD();

  try {
    await playEvents(book.events);
    $winLog.textContent = win > 0 ? `Round win ${fmt(win)}` : 'No win — spin again!';
  } catch (err) {
    console.error('Round animation failed', err);
    $winLog.textContent = 'Animation interrupted. Your demo result has been credited.';
  } finally {
    // The selected book settles once, even if its visual playback fails.
    state.balance = round2(state.balance + win);
    state.lastWin = round2(win);
    updateHUD();
    $btnSpin.classList.remove('free-mode');
    $spinText.textContent = 'SPIN';
    $freeSpinsBar.style.display = 'none';
    setSpinning(false);
  }
}

function round2(n) { return Math.round(n * 100) / 100; }

$btnBetDown.addEventListener('click', () => {
  AudioFX.click();
  const idx = BET_PRESETS.findIndex(v => Math.abs(v - state.bet) < 0.001);
  state.bet = BET_PRESETS[Math.max(0, idx - 1)];
  updateHUD();
});
$btnBetUp.addEventListener('click', () => {
  AudioFX.click();
  const idx = BET_PRESETS.findIndex(v => Math.abs(v - state.bet) < 0.001);
  state.bet = BET_PRESETS[Math.min(BET_PRESETS.length - 1, idx + 1)];
  updateHUD();
});
$btnMute.addEventListener('click', () => {
  state.muted = !state.muted;
  $btnMute.textContent = state.muted ? '🔇' : '🔊';
  $btnMute.classList.toggle('muted', state.muted);
  $btnMute.setAttribute('aria-pressed', String(state.muted));
  $btnMute.setAttribute('aria-label', state.muted ? 'Unmute sound' : 'Mute sound');
  AudioFX.mute(state.muted);
});
$btnTurbo.addEventListener('click', () => {
  state.turbo = !state.turbo;
  $btnTurbo.classList.toggle('active', state.turbo);
  $btnTurbo.setAttribute('aria-pressed', String(state.turbo));
});
$btnMenu.addEventListener('click', () => {
  $infoPanel.hidden = !$infoPanel.hidden;
  $btnMenu.setAttribute('aria-expanded', String(!$infoPanel.hidden));
});
$btnSpin.addEventListener('click', () => doPlay('base'));
$btnBonusBuy.addEventListener('click', () => doPlay('bonus'));
$btnDeposit.addEventListener('click', () => {
  AudioFX.click();
  state.balance = round2(state.balance + 1000);
  updateHUD();
});
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !e.repeat && !e.altKey && !e.ctrlKey && !e.metaKey &&
      !e.target.closest('button, input, textarea, select, a, [contenteditable], [role="button"]')) {
    e.preventDefault();
    doPlay('base');
  }
});

async function loadJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(url + ' ' + res.status);
  return res.json();
}
async function loadText(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(url + ' ' + res.status);
  return res.text();
}

async function init() {
  buildGrid();
  updateHUD();
  setSpinning(false);
  $winLog.textContent = 'Loading game…';
  try {
    const [cfg, baseLut, bonusLut, baseBooks, bonusBooks] = await Promise.all([
      loadJson('game_config.json').catch(() => ({})),
      loadText('lookUpTable_base.csv'),
      loadText('lookUpTable_bonus.csv'),
      loadJson('books_base.json'),
      loadJson('books_bonus.json'),
    ]);
    math.config = cfg;
    math.baseLut = parseLut(baseLut);
    math.bonusLut = parseLut(bonusLut);
    math.baseBooks = baseBooks;
    math.bonusBooks = bonusBooks;
    validateMode(math.baseLut, math.baseBooks);
    validateMode(math.bonusLut, math.bonusBooks);
    state.ready = true;
    setSpinning(false);
    $winLog.textContent = 'Ready — demo chips only. Press SPIN or Spacebar.';
    // Display a representative board before the first spin; it has no payout.
    const preview = baseBooks[0].events.find(event => event.type === 'reveal');
    if (preview) {
      for (let reel = 0; reel < 5; reel++) {
        for (let row = 0; row < 3; row++) paintCell(row, reel, preview.board[reel]?.[row]);
      }
    }
  } catch (err) {
    state.ready = false;
    setSpinning(false);
    console.error('Could not load game data', err);
    $winLog.textContent = 'Could not load game data. Reload the page to try again.';
  }
}

init();
/* Vice Heist — Stake book player (static, no Flask) */


