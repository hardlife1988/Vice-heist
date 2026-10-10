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
  W: 'Wild', S: 'Scatter', B: 'Safe', G: 'Gold Bars',
  D: 'Diamond', R: 'Pink Gem', E: 'Cash', C: 'King', P: 'Ace', H: 'Queen',
};

let math = {
  baseBooks: [],
  bonusBooks: [],
  baseLut: [],
  bonusLut: [],
  config: { rtpBase: 96, maxWin: 10000 },
};

let state = {
  balance: 1000000000,
  currency: 'USD',
  bet: 1000000,
  spinning: false,
  ready: false,
  turbo: false,
  lastWin: 0,
  muted: false,
};

let BET_PRESETS = [10000,20000,50000,100000,200000,400000,1000000,2000000,5000000,10000000,20000000,50000000,100000000];
let rgs = null;
let replayRound = null;

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
function fmt(n) { return StakeMoney.format(n, state.currency); }
function centsToCash(units) { return StakeMoney.payout(units, state.bet); }
function renderPaytable() {
  const top = $('top-payouts'); const body = $('paytable-body');
  top.replaceChildren(); body.replaceChildren();
  $('rtp-details').textContent='Base RTP '+math.config.rtpBase.toFixed(4)+'% · Bonus Buy RTP '+math.config.rtpBonus.toFixed(4)+'%';
  $('payline-details').textContent='Payline rows (top = 1, middle = 2, bottom = 3): '+Object.entries(math.config.paylinePaths||{}).map(([id,rows])=>id+': '+rows.map(r=>r+1).join('–')).join(' · ');
  for (const code of [...Object.keys(math.config.paytable), 'S']) {
    const card = document.createElement('div'); card.className = 'payout-symbol';
    const img = document.createElement('img'); img.src = SYMBOL_ASSETS[code]; img.alt = SYMBOL_NAME[code]; card.append(img);
    const text = document.createElement('div'); const name = document.createElement('strong'); name.textContent=SYMBOL_NAME[code];text.append(name);
    const row = document.createElement('tr');const label=document.createElement('td');label.textContent=SYMBOL_NAME[code];row.append(label);
    if(code==='S') {const description=document.createElement('span');description.textContent='3+ → 10 free spins';text.append(description);const td=document.createElement('td');td.colSpan=3;td.textContent='3 / 4 / 5+ anywhere: 2× / 5× / 10× + 10 free spins';row.append(td);}
    else for(const count of [3,4,5]) {const value=math.config.paytable[code][count];const line=document.createElement('span');line.textContent=count+' · '+value+'×';text.append(line);const td=document.createElement('td');td.textContent=value+'×';row.append(td);}
    card.append(text);top.append(card);body.append(row);
  }
}

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
  if($('bet-select')) $('bet-select').value=$('bet-select').tagName==='INPUT'?state.bet/1000000:state.bet;
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
  if($('bet-select')) $('bet-select').disabled=on;
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
        state.lastWin = centsToCash(ev.amount || 0);
        updateHUD();
        if(ev.type === 'finalWin') showWinBanner(state.lastWin);
        break;
      default:
        break;
    }
    if(rgs) await rgs.checkpoint(ev.index);
  }
}

async function doPlay(mode) {
  if (state.spinning || !state.ready) return;
  AudioFX.unlock();
  if(replayRound){setSpinning(true);state.lastWin=0;try{await playEvents(replayRound.events);$winLog.textContent='Replay complete — no wager placed.';}finally{setSpinning(false);$spinText.textContent='REPLAY';}return;}
  if(mode==='bonus'&&state.flags?.disabledBuyFeature)return;
  const cost = mode === 'bonus' ? state.bet * 100 : state.bet;
  if (state.balance < cost) {
    $winLog.textContent = rgs?'Insufficient wallet balance.':'Insufficient demo balance — add chips below.';
    return;
  }
  setSpinning(true);
  state.lastWin = 0; updateHUD(); showWinBanner(0);
  try {
    const started=Date.now();
    let events, win;
    if(rgs) {
      const data = await rgs.play(state.bet,mode);state.balance=data.balance.amount;
      events=rgs.events(data.round);win=data.round.payout ?? centsToCash(events.at(-1).amount);
    } else {
      const book=pickWeighted(mode==='bonus'?math.bonusLut:math.baseLut,mode==='bonus'?math.bonusBooks:math.baseBooks);
      events=book.events;win=centsToCash(book.payoutMultiplier);state.balance-=cost;
    }
    updateHUD();
    try { await playEvents(events);
      const duration=state.flags?.minimumRoundDuration||0;if(Date.now()-started<duration)await new Promise(resolve=>setTimeout(resolve,duration-(Date.now()-started)));
    } finally {
      if(rgs){const settled=await rgs.finish();if(settled)state.balance=settled.balance.amount;}
      else state.balance=StakeMoney.safe(state.balance+win);
      state.lastWin=StakeMoney.safe(win);updateHUD();
    }
    $winLog.textContent=win>0?'Round win '+fmt(win):'No win — spin again!';
  } catch(err) {
    console.error(err);$winLog.textContent=err.message;
    if(rgs){state.ready=false;$winLog.textContent+=' — Reload to recover your Stake session. Your wager will not be retried.';}
  } finally {
    $btnSpin.classList.remove('free-mode');$spinText.textContent='SPIN';$freeSpinsBar.style.display='none';setSpinning(false);
  }
}

function round2(n) { return Math.round(n * 100) / 100; }

$btnBetDown.addEventListener('click', () => {
  AudioFX.click();
  if(rgs && !rgs.levels.length){state.bet=Math.max(rgs.config.minBet,state.bet-rgs.config.stepBet);}else {const idx=BET_PRESETS.indexOf(state.bet);state.bet=BET_PRESETS[Math.max(0,idx-1)];}
  updateHUD();
});
$btnBetUp.addEventListener('click', () => {
  AudioFX.click();
  if(rgs && !rgs.levels.length){state.bet=Math.min(rgs.config.maxBet,state.bet+rgs.config.stepBet);}else {const idx=BET_PRESETS.indexOf(state.bet);state.bet=BET_PRESETS[Math.min(BET_PRESETS.length-1,idx+1)];}
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
$btnBonusBuy.addEventListener('click', () => {
  if(state.spinning || !state.ready) return;
  $('bonus-confirm-cost').textContent='Cost: '+fmt(state.bet*100)+' · Ordinary bet: '+fmt(state.bet);
  $('bonus-confirm').showModal();
});
$('bonus-cancel').addEventListener('click',()=> $('bonus-confirm').close());
$('bonus-accept').addEventListener('click',()=> {$('bonus-confirm').close();doPlay('bonus');});
$btnDeposit.addEventListener('click', () => {
  AudioFX.click();
  if(rgs) return;
  state.balance = StakeMoney.safe(state.balance + 1000000000);
  updateHUD();
});
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !e.repeat && !e.altKey && !e.ctrlKey && !e.metaKey &&
      !e.target.closest('button, input, textarea, select, a, [contenteditable], [role="button"]')) {
    e.preventDefault();
    if(!state.flags?.disabledSpacebar) doPlay('base');
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
    const cfg=await loadJson('game_config.json');math.config=cfg;renderPaytable();
    const params=new URLSearchParams(location.search);
    if(params.get('replay')==='true') {
      const raw=params.get('rgs_url');if(!raw)throw Error('Missing replay RGS URL');
      const url=new URL(raw.includes('://')?raw:'https://'+raw);if(url.protocol!=='https:' && !['localhost','127.0.0.1'].includes(url.hostname))throw Error('Invalid replay URL');
      const parts=['game','version','mode','event'].map(k=>{const value=params.get(k);if(!value)throw Error('Missing replay '+k);return encodeURIComponent(value);});
      const response=await fetch(url.href.replace(/\/$/,'')+'/bet/replay/'+parts.join('/'));if(!response.ok)throw Error('Replay unavailable');
      const data=await response.json();replayRound={events:StakeRGS.prototype.events.call(null,data)};
      state.bet=StakeMoney.safe(Number(params.get('amount')||1000000));state.currency=params.get('currency')||'USD';
      document.querySelector('.demo-tools').hidden=true;$btnBonusBuy.hidden=true;$btnBetDown.hidden=true;$btnBetUp.hidden=true;document.querySelector('.hud-balance').hidden=true;$spinText.textContent='REPLAY';
    } else if(params.has('sessionID') || params.has('rgs_url')) {
      rgs=new StakeRGS(params);const auth=await rgs.authenticate();state.balance=auth.balance.amount;state.currency=auth.balance.currency;state.bet=auth.config.defaultBetLevel;
      BET_PRESETS=rgs.levels.length?[...rgs.levels].sort((a,b)=>a-b):[auth.config.minBet,auth.config.defaultBetLevel,auth.config.maxBet].filter((v,i,a)=>a.indexOf(v)===i).sort((a,b)=>a-b);
      document.querySelector('.demo-tools').hidden=true;
      if(auth.jurisdictionFlags?.disabledBuyFeature) $btnBonusBuy.hidden=true;
      const flags=auth.jurisdictionFlags||{};state.flags=flags;state.sessionStart=Date.now();state.sessionBalance=state.balance;
      if(flags.displayRTP===false){document.querySelector('.header-badge-rtp').hidden=true;$('rtp-details').hidden=true;document.querySelectorAll('.info-badges span').forEach(el=>{if(/RTP/i.test(el.textContent))el.hidden=true;});document.querySelectorAll('.paytable-note').forEach(el=>{el.textContent=el.textContent.replace(/Base and Bonus Buy modes are calibrated to a 96% RTP target\.\s*/,'').replace(/RTP is a long-run average, not a promise for a session\./,'');});}
      if(flags.displaySessionTimer || flags.displayNetPosition) setInterval(()=>{const details=[];if(flags.displaySessionTimer)details.push('Session '+Math.floor((Date.now()-state.sessionStart)/60000)+' min');if(flags.displayNetPosition)details.push('Net '+(state.balance<state.sessionBalance?'−':'+')+fmt(Math.abs(state.balance-state.sessionBalance)));$('session-details').textContent=details.join(' · ');},1000);
      if(flags.disabledTurbo){state.turbo=false;$btnTurbo.hidden=true;}
      const select=document.createElement('select');select.setAttribute('aria-label','Stake bet amount');select.id='bet-select';
      for(const bet of BET_PRESETS){const option=document.createElement('option');option.value=bet;option.textContent=fmt(bet);select.append(option);}select.value=state.bet;
      select.addEventListener('change',()=>{if(state.spinning)return;state.bet=Number(select.value);updateHUD();});document.querySelector('.rail-bet').append(select);
      if(!rgs.levels.length){
        select.remove();const input=document.createElement('input');input.type='number';input.id='bet-select';input.setAttribute('aria-label','Stake bet amount in wallet units');input.min=auth.config.minBet/1000000;input.max=auth.config.maxBet/1000000;input.step=auth.config.stepBet/1000000;input.value=state.bet/1000000;
        input.addEventListener('change',()=>{if(state.spinning)return;try{const value=Math.round(Number(input.value)*1000000);rgs.validBet(value);state.bet=value;updateHUD();}catch(error){input.value=state.bet/1000000;$winLog.textContent=error.message;}});document.querySelector('.rail-bet').append(input);
      }
      if(rgs.round){
        state.bet=rgs.round.amount ?? state.bet;setSpinning(true);const events=rgs.events(rgs.round);const checkpoint=Number(rgs.round.event);const resume=Number.isInteger(checkpoint)&&rgs.round.event!==undefined&&rgs.round.event!==''?checkpoint:-1;
        for(const event of events.filter(e=>e.index<=resume)){if(event.type==='reveal')await playReveal(event);if(event.type==='setTotalWin')state.lastWin=centsToCash(event.amount);}
        updateHUD();await playEvents(events.filter(e=>e.index>resume));const result=await rgs.finish();if(result)state.balance=result.balance.amount;setSpinning(false);
      }
    } else {
      if(cfg.requiresRGS)throw Error('Launch this game from a valid Stake session.');
      const [baseLut,bonusLut,baseBooks,bonusBooks]=await Promise.all([loadText('lookUpTable_base.csv'),loadText('lookUpTable_bonus.csv'),loadJson('books_base.json'),loadJson('books_bonus.json')]);
      math.baseLut=parseLut(baseLut);math.bonusLut=parseLut(bonusLut);math.baseBooks=baseBooks;math.bonusBooks=bonusBooks;
      validateMode(math.baseLut,baseBooks);validateMode(math.bonusLut,bonusBooks);
    }
    updateHUD();
    state.ready = true;
    setSpinning(false);
    $winLog.textContent = replayRound?'Replay ready — press REPLAY.':rgs?'Ready — '+state.currency+' wallet connected.':'Ready — demo chips only. Press SPIN or Spacebar.';
    // Display a representative board before the first spin; it has no payout.
    const preview = math.baseBooks[0]?.events.find(event => event.type === 'reveal');
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


