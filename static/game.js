/* Vice Heist — Stake book player (static, no Flask) */
'use strict';

const SYMBOL_EMOJI = {
  W: '🃏', S: '📖', B: '📚', G: '🪙',
  D: '💎', R: '🔴', E: '💚', C: '♣', P: '♠', H: '♥',
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
  totalWon: 0,
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

const AudioFX = {
  ctx: null, spinning: false, spinTimer: null,
  unlock() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
    }
    if (this.ctx.state === 'suspended') this.ctx.resume();
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
    o.connect(g); g.connect(this.ctx.destination);
    o.start(t); o.stop(t + dur);
  },
  click() { this.unlock(); this.beep(420, 0.05, 'square', 0.04); },
  reelStop() { this.unlock(); this.beep(180, 0.08, 'triangle', 0.07); },
  scatter() { this.unlock(); this.beep(880, 0.18, 'sine', 0.06); this.beep(1320, 0.22, 'sine', 0.04, 0.08); },
  win(amount, bet) {
    this.unlock();
    this.beep(520, 0.12, 'triangle', 0.06);
    this.beep(780, 0.16, 'triangle', 0.05, 0.08);
    if (amount >= bet * 5) this.beep(1040, 0.28, 'sawtooth', 0.04, 0.16);
  },
  bonus() {
    this.unlock();
    [523, 659, 784, 1046].forEach((f, i) => this.beep(f, 0.2, 'triangle', 0.05, i * 0.09));
  },
};

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function fmt(n) { return '$' + Number(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
function centsToCash(cents) { return (cents / 100) * state.bet; }

function parseLut(text) {
  return text.trim().split(/\n+/).map(line => {
    const [id, weight, payout] = line.split(',').map(Number);
    return { id, weight, payout };
  }).filter(r => r.id);
}

function pickWeighted(lut, books) {
  const total = lut.reduce((s, r) => s + (r.weight || 1), 0);
  let roll = Math.random() * total;
  let chosen = lut[0];
  for (const row of lut) {
    roll -= row.weight || 1;
    if (roll <= 0) { chosen = row; break; }
  }
  const book = books.find(b => b.id === chosen.id) || books[chosen.id - 1];
  return book || books[0];
}

function parseCsvOrJsonBooks() { /* placeholder */ }

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
  const code = typeof sym === 'object' ? (sym.name || '?') : (sym || '?');
  cell.dataset.sym = code;
  cell.classList.remove('win-cell', 'spinning', 'landed');
  if (extraClass) cell.classList.add(extraClass);
  cell.innerHTML = `<span class="sym-ico">${SYMBOL_EMOJI[code] || code}</span><span class="sym-name">${SYMBOL_NAME[code] || ''}</span>`;
}

function highlightWins(positions) {
  document.querySelectorAll('.reel-cell').forEach(c => c.classList.remove('win-cell'));
  (positions || []).forEach(p => {
    document.getElementById(`cell-${p.row}-${p.reel}`)?.classList.add('win-cell');
  });
}

function updateHUD() {
  $balance.textContent = fmt(state.balance);
  $totalWin.textContent = fmt(state.totalWon);
  $betValue.textContent = fmt(state.bet);
  $bonusCost.textContent = fmt(state.bet * 100);
}

function showWinBanner(amount) {
  if (amount <= 0) { $winBanner.style.display = 'none'; $winBanner.classList.remove('big'); return; }
  const big = amount >= state.bet * 5;
  $winBannerText.textContent = (big ? 'BIG WIN  ' : 'WIN  ') + fmt(amount);
  $winBanner.classList.toggle('big', big);
  $winBanner.style.display = 'block';
  clearTimeout(showWinBanner._t);
  showWinBanner._t = setTimeout(() => { $winBanner.style.display = 'none'; }, 3500);
}

function setSpinning(on) {
  state.spinning = on;
  $btnSpin.disabled = on;
  $btnBetDown.disabled = on;
  $btnBetUp.disabled = on;
  $btnBonusBuy.disabled = on;
}

async function playReveal(event) {
  const board = event.board || [];
  for (let reel = 0; reel < 5; reel++) {
    AudioFX.reelStop();
    const col = board[reel] || [];
    for (let row = 0; row < 3; row++) {
      paintCell(row, reel, col[row], 'landed');
    }
    await sleep(90 + reel * 25);
  }
}

async function playEvents(events) {
  let log = [];
  for (const ev of events) {
    switch (ev.type) {
      case 'reveal':
        await playReveal(ev);
        break;
      case 'winInfo': {
        const cash = centsToCash(ev.totalWin || 0);
        const positions = [];
        (ev.wins || []).forEach(w => (w.positions || []).forEach(p => positions.push(p)));
        highlightWins(positions);
        (ev.wins || []).forEach(w => {
          if (w.meta && w.meta.scatter) log.push(`<span class="scatter-line">📖 ${w.kind} Scatters → ${fmt(centsToCash(w.win))}</span>`);
          else log.push(`<span class="win-line">${w.kind}× ${w.symbol} → ${fmt(centsToCash(w.win))}</span>`);
        });
        $winLog.innerHTML = log.join('<br>') || '';
        if (cash > 0) AudioFX.win(cash, state.bet);
        await sleep(280);
        break;
      }
      case 'freeSpinTrigger':
        AudioFX.scatter();
        $freeSpinsBar.style.display = 'block';
        $fsCount.textContent = ev.totalFs || 10;
        $btnSpin.classList.add('free-mode');
        $btnSpin.textContent = 'FREE';
        log.push(`<span class="scatter-line">⚡ ${ev.totalFs} FREE SPINS</span>`);
        $winLog.innerHTML = log.join('<br>');
        await sleep(450);
        break;
      case 'updateFreeSpin':
        $freeSpinsBar.style.display = 'block';
        $fsCount.textContent = `${ev.amount}/${ev.total}`;
        $btnSpin.textContent = `FREE (${ev.total - ev.amount})`;
        await sleep(80);
        break;
      case 'enterBonus':
        AudioFX.bonus();
        log.push('<span class="scatter-line">BONUS BUY — entering free spins</span>');
        $winLog.innerHTML = log.join('<br>');
        await sleep(300);
        break;
      case 'freeSpinEnd':
        $btnSpin.classList.remove('free-mode');
        $btnSpin.textContent = 'SPIN';
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
  if (state.spinning) return;
  AudioFX.unlock();
  const cost = mode === 'bonus' ? state.bet * 100 : state.bet;
  if (state.balance < cost) {
    $winLog.innerHTML = '<span style="color:var(--red)">Insufficient balance — add chips below.</span>';
    return;
  }
  const lut = mode === 'bonus' ? math.bonusLut : math.baseLut;
  const books = mode === 'bonus' ? math.bonusBooks : math.baseBooks;
  if (!books.length) {
    $winLog.innerHTML = '<span style="color:var(--red)">Math books not loaded.</span>';
    return;
  }

  setSpinning(true);
  $winLog.innerHTML = '';
  showWinBanner(0);
  if (mode === 'bonus') AudioFX.bonus();
  state.balance = round2(state.balance - cost);
  updateHUD();

  const book = pickWeighted(lut, books);
  await playEvents(book.events || []);
  const win = centsToCash(book.payoutMultiplier || 0);
  state.balance = round2(state.balance + win);
  state.totalWon = round2(state.totalWon + win);
  updateHUD();
  if (!(book.events || []).some(e => e.type === 'winInfo' || e.type === 'finalWin')) {
    $winLog.innerHTML = '<span style="color:var(--text-dim)">No win — spin again!</span>';
  }
  $btnSpin.classList.remove('free-mode');
  $btnSpin.textContent = 'SPIN';
  $freeSpinsBar.style.display = 'none';
  setSpinning(false);
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
  if (!state.muted) AudioFX.unlock();
});
$btnSpin.addEventListener('click', () => doPlay('base'));
$btnBonusBuy.addEventListener('click', () => doPlay('bonus'));
$btnDeposit.addEventListener('click', () => {
  AudioFX.click();
  state.balance = round2(state.balance + 1000);
  updateHUD();
});
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
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
    $winLog.innerHTML = `Loaded ${baseBooks.length} base + ${bonusBooks.length} bonus books. Press SPIN.`;
    if (cfg.rtpBase) {
      const chip = document.querySelector('.chip');
      if (chip) chip.textContent = `RTP ${cfg.rtpBase}%`;
    }
  } catch (err) {
    $winLog.innerHTML = `<span style="color:var(--red)">Could not load Stake books: ${err.message}. Run <code>python math/build_stake_bundle.py</code>.</span>`;
  }
}

init();
