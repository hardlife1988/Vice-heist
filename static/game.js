/* ── Vice Heist — Frontend Game Logic ──────────────────────────────────────── */
'use strict';

// ── Symbol map ────────────────────────────────────────────────────────────────
const SYMBOL_EMOJI = {
  W: '🃏', S: '📖', B: '📚', G: '🪙',
  D: '💎', R: '🔴', E: '💚', C: '♣', P: '♠', H: '♥',
};
const SYMBOL_NAME = {
  W: 'Wild', S: 'Scatter', B: 'Book', G: 'Gold Bar',
  D: 'Diamond', R: 'Ruby', E: 'Emerald', C: 'Club', P: 'Spade', H: 'Heart',
};

// ── State ─────────────────────────────────────────────────────────────────────
let state = {
  balance: 1000,
  bet: 1.00,
  betStep: 0.20,
  minBet: 0.20,
  maxBet: 100.00,
  spinning: false,
  inFreeSpin: false,
  freeSpinsRemaining: 0,
  totalWon: 0,
  lastSpin: null,          // full API response for last spin
  revealedServerSeed: null,
};

const BET_PRESETS = [0.20, 0.40, 1.00, 2.00, 5.00, 10.00, 20.00, 50.00, 100.00];

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $balance        = document.getElementById('balance');
const $totalWin       = document.getElementById('total-win');
const $betValue       = document.getElementById('bet-value');
const $bonusCost      = document.getElementById('bonus-cost');
const $reelsGrid      = document.getElementById('reels-grid');
const $winBanner      = document.getElementById('win-banner');
const $winBannerText  = document.getElementById('win-banner-text');
const $freeSpinsBar   = document.getElementById('free-spins-bar');
const $fsCount        = document.getElementById('fs-count');
const $winLog         = document.getElementById('win-log');
const $btnSpin        = document.getElementById('btn-spin');
const $btnBetDown     = document.getElementById('bet-down');
const $btnBetUp       = document.getElementById('bet-up');
const $btnBonusBuy    = document.getElementById('btn-bonus-buy');
const $btnDeposit     = document.getElementById('btn-deposit');

// Provably fair
const $pfHash         = document.getElementById('pf-server-seed-hash');
const $pfClientSeed   = document.getElementById('pf-client-seed');
const $pfNonce        = document.getElementById('pf-nonce');
const $btnUpdateSeed  = document.getElementById('btn-update-seed');
const $pfReveal       = document.getElementById('pf-reveal');
const $pfRevealedSeed = document.getElementById('pf-revealed-seed');
const $btnVerifyLast  = document.getElementById('btn-verify-last');
const $pfVerifyResult = document.getElementById('pf-verify-result');
const $btnManualVerify= document.getElementById('btn-manual-verify');
const $manualResult   = document.getElementById('manual-verify-result');

// ── Build reel grid ───────────────────────────────────────────────────────────
function buildGrid() {
  $reelsGrid.innerHTML = '';
  // 3 rows, 5 reels — grid is row-major in CSS but we store cells by [row][reel]
  for (let row = 0; row < 3; row++) {
    for (let reel = 0; reel < 5; reel++) {
      const cell = document.createElement('div');
      cell.className = 'reel-cell';
      cell.id = `cell-${row}-${reel}`;
      cell.textContent = '?';
      $reelsGrid.appendChild(cell);
    }
  }
}

function updateGrid(grid, winCells = []) {
  // grid: 3×5 array of symbol value strings
  for (let row = 0; row < 3; row++) {
    for (let reel = 0; reel < 5; reel++) {
      const sym = grid[row][reel];
      const cell = document.getElementById(`cell-${row}-${reel}`);
      cell.textContent = SYMBOL_EMOJI[sym] || sym;
      cell.dataset.sym = sym;
      cell.classList.remove('win-cell', 'spinning');
      void cell.offsetWidth; // force reflow for animation restart
      cell.classList.add('spinning');
    }
  }
  // Highlight winning cells after a short delay
  if (winCells.length) {
    setTimeout(() => {
      winCells.forEach(([row, reel]) => {
        document.getElementById(`cell-${row}-${reel}`)?.classList.add('win-cell');
      });
    }, 350);
  }
}

// ── UI helpers ─────────────────────────────────────────────────────────────────
function fmt(n) {
  return '$' + Number(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function updateHUD() {
  $balance.textContent = fmt(state.balance);
  $totalWin.textContent = fmt(state.totalWon);
  $betValue.textContent = fmt(state.bet);
  $bonusCost.textContent = fmt(state.bet * 100);
  $btnSpin.classList.toggle('free-mode', state.inFreeSpin);
  $btnSpin.textContent = state.inFreeSpin ? `FREE SPIN (${state.freeSpinsRemaining})` : 'SPIN';
  $freeSpinsBar.style.display = state.inFreeSpin ? 'block' : 'none';
  $fsCount.textContent = state.freeSpinsRemaining;
}

function showWinBanner(amount) {
  if (amount <= 0) { $winBanner.style.display = 'none'; return; }
  $winBannerText.textContent = `WIN  ${fmt(amount)}`;
  $winBanner.style.display = 'block';
  clearTimeout(showWinBanner._t);
  showWinBanner._t = setTimeout(() => $winBanner.style.display = 'none', 4000);
}

function setSpinning(active) {
  state.spinning = active;
  $btnSpin.disabled = active;
  $btnBetDown.disabled = active;
  $btnBetUp.disabled = active;
  $btnBonusBuy.disabled = active;
}

// ── Bet controls ──────────────────────────────────────────────────────────────
function adjustBet(dir) {
  const idx = BET_PRESETS.findIndex(v => Math.abs(v - state.bet) < 0.001);
  let next = idx + dir;
  next = Math.max(0, Math.min(BET_PRESETS.length - 1, next));
  state.bet = BET_PRESETS[next];
  updateHUD();
}

$btnBetDown.addEventListener('click', () => adjustBet(-1));
$btnBetUp.addEventListener('click',   () => adjustBet(+1));

// ── Spin ──────────────────────────────────────────────────────────────────────
async function doSpin(bonusBuy = false) {
  if (state.spinning) return;

  const cost = bonusBuy ? state.bet * 100 : (state.inFreeSpin ? 0 : state.bet);
  if (state.balance < cost) {
    $winLog.innerHTML = '<span style="color:var(--red)">Insufficient balance — add chips below.</span>';
    return;
  }

  setSpinning(true);
  $winLog.innerHTML = '';
  showWinBanner(0);

  // Show blank-ish grid while "spinning"
  const blankGrid = Array.from({length: 3}, () => Array(5).fill('?'));
  // Show loading emoji
  for (let r = 0; r < 3; r++) for (let c = 0; c < 5; c++) {
    const cell = document.getElementById(`cell-${r}-${c}`);
    cell.textContent = '⟳';
    cell.classList.remove('win-cell');
  }

  try {
    const res = await fetch('/api/spin', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ bet: state.bet, bonus_buy: bonusBuy }),
    });
    const data = await res.json();

    if (data.error) {
      $winLog.innerHTML = `<span style="color:var(--red)">${data.error}</span>`;
      setSpinning(false);
      return;
    }

    state.lastSpin = data;
    state.balance = data.balance;
    state.inFreeSpin = data.in_free_spins;
    state.freeSpinsRemaining = data.free_spins_remaining;
    state.totalWon += data.win;

    // Determine win cells (all cells on winning paylines)
    const winCells = computeWinCells(data.payline_wins, data.reel_grid);

    updateGrid(data.reel_grid, winCells);
    updateHUD();
    updatePF(data);
    renderWinLog(data);
    showWinBanner(data.win);

    // Auto-play free spins with short delay
    if (state.inFreeSpin && state.freeSpinsRemaining > 0) {
      setTimeout(() => { setSpinning(false); doSpin(false); }, 900);
    } else {
      setSpinning(false);
    }

  } catch (err) {
    $winLog.innerHTML = `<span style="color:var(--red)">Network error: ${err.message}</span>`;
    setSpinning(false);
  }
}

$btnSpin.addEventListener('click', () => doSpin(false));
$btnBonusBuy.addEventListener('click', () => doSpin(true));
$btnDeposit.addEventListener('click', async () => {
  const r = await fetch('/api/deposit', { method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ amount: 1000 }) });
  const d = await r.json();
  state.balance = d.balance;
  updateHUD();
});

// ── Payline helpers ───────────────────────────────────────────────────────────
// PAYLINES mirrors server paytable.py PAYLINES dict
const PAYLINES = {
  1:[1,1,1,1,1], 2:[0,0,0,0,0], 3:[2,2,2,2,2],
  4:[0,1,2,1,0], 5:[2,1,0,1,2],
  6:[0,0,1,0,0], 7:[2,2,1,2,2],
  8:[0,1,1,1,0], 9:[2,1,1,1,2],
  10:[1,0,1,0,1], 11:[1,2,1,2,1],
  12:[0,1,0,1,0], 13:[2,1,2,1,2],
  14:[0,0,1,2,2], 15:[2,2,1,0,0],
  16:[0,1,2,2,2], 17:[2,1,0,0,0],
  18:[1,1,0,1,1], 19:[1,1,2,1,1],
  20:[0,2,0,2,0],
};

function computeWinCells(paylineWins, grid) {
  const cells = new Set();
  paylineWins.forEach(pw => {
    const line = PAYLINES[pw.payline];
    if (!line) return;
    for (let reel = 0; reel < pw.count; reel++) {
      cells.add(`${line[reel]}-${reel}`);
    }
  });
  return [...cells].map(k => k.split('-').map(Number));
}

function renderWinLog(data) {
  const lines = [];
  if (data.is_free_spin) lines.push(`<span style="color:var(--green)">⚡ Free Spin ×${data.multiplier}</span>`);
  data.payline_wins.forEach(pw => {
    lines.push(`<span class="win-line">Line ${pw.payline}: ${pw.count}× ${pw.symbol} → ${fmt(pw.win)}</span>`);
  });
  if (data.scatter_count >= 3) {
    if (data.triggers_free_spins) {
      lines.push(`<span class="scatter-line">📖 ${data.scatter_count} Scatters → 10 FREE SPINS!</span>`);
    } else if (data.scatter_win > 0) {
      lines.push(`<span class="scatter-line">📖 ${data.scatter_count} Scatters → ${fmt(data.scatter_win)}</span>`);
    }
  }
  if (!lines.length) {
    lines.push('<span style="color:var(--text-dim)">No win — spin again!</span>');
  }
  $winLog.innerHTML = lines.join('<br>');
}

// ── Provably fair UI ──────────────────────────────────────────────────────────
function updatePF(data) {
  $pfHash.value   = data.server_seed_hash  || $pfHash.value;
  $pfClientSeed.value = data.client_seed   || $pfClientSeed.value;
  $pfNonce.value  = data.nonce !== undefined ? data.nonce : $pfNonce.value;
}

$btnUpdateSeed.addEventListener('click', async () => {
  const newSeed = $pfClientSeed.value.trim();
  if (!newSeed) return;
  const res = await fetch('/api/seed', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ client_seed: newSeed }),
  });
  const data = await res.json();
  if (data.error) { alert(data.error); return; }

  $pfHash.value        = data.new_server_seed_hash;
  $pfClientSeed.value  = data.client_seed;
  $pfNonce.value       = '0';

  // Show revealed seed panel
  state.revealedServerSeed = data.revealed_server_seed;
  $pfRevealedSeed.value = data.revealed_server_seed;
  $pfReveal.style.display = 'block';
  $pfVerifyResult.style.display = 'none';
});

$btnVerifyLast.addEventListener('click', async () => {
  if (!state.lastSpin || !state.revealedServerSeed) {
    alert('Make at least one spin first, then rotate the seed to verify it.');
    return;
  }
  await runVerify(
    state.revealedServerSeed,
    state.lastSpin.client_seed,
    state.lastSpin.nonce,
    state.lastSpin.reel_grid,
    $pfVerifyResult
  );
});

$btnManualVerify.addEventListener('click', async () => {
  const serverSeed = document.getElementById('v-server-seed').value.trim();
  const clientSeed = document.getElementById('v-client-seed').value.trim();
  const nonce      = parseInt(document.getElementById('v-nonce').value, 10);
  const gridRaw    = document.getElementById('v-grid').value.trim();

  if (!serverSeed || !clientSeed || isNaN(nonce) || !gridRaw) {
    $manualResult.textContent = 'Fill in all fields.';
    $manualResult.className = 'pf-verify-result fail';
    $manualResult.style.display = 'block';
    return;
  }
  let grid;
  try { grid = JSON.parse(gridRaw); } catch {
    $manualResult.textContent = 'Invalid JSON for reel grid.';
    $manualResult.className = 'pf-verify-result fail';
    $manualResult.style.display = 'block';
    return;
  }
  await runVerify(serverSeed, clientSeed, nonce, grid, $manualResult);
});

async function runVerify(serverSeed, clientSeed, nonce, grid, $el) {
  try {
    const res = await fetch('/api/verify', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ server_seed: serverSeed, client_seed: clientSeed, nonce, reel_grid: grid }),
    });
    const data = await res.json();
    if (data.verified) {
      $el.textContent = '✅ VERIFIED — The spin result matches the provably fair hash.\n\nSpin hash: ' + data.spin_hash;
      $el.className = 'pf-verify-result ok';
    } else {
      $el.textContent = '❌ FAILED — Spin result does NOT match.\n\nExpected: ' +
        JSON.stringify(data.expected_grid) + '\nProvided: ' + JSON.stringify(data.provided_grid) +
        '\n\nSpin hash: ' + data.spin_hash;
      $el.className = 'pf-verify-result fail';
    }
    $el.style.display = 'block';
  } catch (err) {
    $el.textContent = 'Verification request failed: ' + err.message;
    $el.className = 'pf-verify-result fail';
    $el.style.display = 'block';
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  buildGrid();
  try {
    const res  = await fetch('/api/config');
    const data = await res.json();
    state.balance            = data.balance ?? 1000;
    state.bet                = data.default_bet ?? 1.00;
    state.minBet             = data.min_bet ?? 0.20;
    state.maxBet             = data.max_bet ?? 100.00;
    state.inFreeSpin         = data.in_free_spins ?? false;
    state.freeSpinsRemaining = data.free_spins_remaining ?? 0;
    $pfHash.value       = data.server_seed_hash || '';
    $pfClientSeed.value = data.client_seed || '';
    $pfNonce.value      = data.nonce ?? 0;
  } catch (e) {
    console.error('Config fetch failed:', e);
  }
  updateHUD();
}

init();
