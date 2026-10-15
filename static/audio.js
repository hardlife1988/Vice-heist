/* Original Miami noir score. No network audio, randomness, or game outcomes. */
'use strict';
window.HeistAudio = (() => {
  let ctx, bus, timer, next = 0, beat = 0, bonus = false, muted = false, unlocked = false, bed, bedFailed = false;
  const voices = new Set();
  const levels = { music: 0.3, effects: 0.7 };
  try {
    const saved = JSON.parse(localStorage.getItem('vice-heist-audio') || '{}');
    for (const key of Object.keys(levels)) if (Number.isFinite(saved[key])) levels[key] = Math.max(0, Math.min(1, saved[key]));
  } catch (_) { /* Storage is optional in embedded browsers. */ }
  function save() { try { localStorage.setItem('vice-heist-audio', JSON.stringify(levels)); } catch (_) {} }
  function stop() {
    clearInterval(timer); timer = null;
    for (const voice of voices) { try { voice.stop(); } catch (_) {} }
    voices.clear();
  }
  function tone(freq, time, duration, gain, type = 'sine') {
    const osc = ctx.createOscillator(), envelope = ctx.createGain();
    osc.type = type; osc.frequency.value = freq;
    envelope.gain.setValueAtTime(0, time);
    envelope.gain.linearRampToValueAtTime(gain, time + 0.015);
    envelope.gain.exponentialRampToValueAtTime(0.0001, time + duration);
    osc.connect(envelope); envelope.connect(bus); voices.add(osc);
    osc.onended = () => { voices.delete(osc); osc.disconnect(); envelope.disconnect(); };
    osc.start(time); osc.stop(time + duration + 0.02);
  }
  function schedule() {
    if (ctx.state !== 'running') return;
    while (next < ctx.currentTime + 0.18) {
      // 96 BPM, eight-bar phrase in D minor; more pulse during free spins.
      const step = beat % 64, roots = [73.416, 58.270, 65.406, 55.000];
      const root = roots[Math.floor(step / 16)];
      if (step % 4 === 0) {
        tone(root, next, 0.48, 0.22, 'triangle');
        tone(48, next, 0.12, 0.18);
      }
      if (step % 16 === 0) {
        [1, 1.189207, 1.498307].forEach(ratio => tone(root * 4 * ratio, next, 2.3, 0.018, 'sine'));
      }
      if (bonus || step % 4 === 2) {
        const intervals = [2, 2.996614, 2.378414, 4];
        tone(root * intervals[step % 4], next, bonus ? 0.16 : 0.3, bonus ? 0.06 : 0.025, 'triangle');
      }
      beat++; next += 60 / 96 / 2;
    }
  }
  function syncBed(audible) {
    if (bedFailed) return false;
    if (!bed) {
      bed = new Audio('assets/audio/base_loop.mp3');
      bed.loop = true;
      bed.preload = 'auto';
      bed.addEventListener('error', () => { bedFailed = true; bed = null; });
    }
    bed.volume = Math.max(0, Math.min(1, levels.music * (bonus ? 0.72 : 0.5)));
    if (!audible) { bed.pause(); return true; }
    bed.play().catch(() => { bedFailed = true; });
    return !bedFailed;
  }
  function sync() {
    if (!ctx) return;
    const audible = unlocked && !muted && !document.hidden && levels.music > 0;
    bus.gain.setTargetAtTime(audible && bedFailed ? levels.music * 0.65 : 0, ctx.currentTime, 0.12);
    if (!audible) { stop(); if (bed) bed.pause(); return; }
    if (syncBed(true)) { stop(); return; }
    if (!timer) { next = ctx.currentTime + 0.04; schedule(); timer = setInterval(schedule, 75); }
  }
  function unlock() {
    if (muted || document.hidden) return;
    try {
      if (!ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return;
        ctx = new AC(); bus = ctx.createGain(); bus.gain.value = 0; bus.connect(ctx.destination);
      }
      unlocked = true;
      ctx.resume().then(sync).catch(() => {});
    } catch (_) { /* Silent play remains available when audio is unsupported. */ }
  }
  document.addEventListener('visibilitychange', () => {
    sync();
    if (ctx && document.hidden) ctx.suspend().catch(() => {});
    else if (ctx && unlocked && !muted) ctx.resume().then(sync).catch(() => {});
  });
  window.addEventListener('pagehide', stop);
  return {
    unlock,
    mute(on) { muted = on; if (!on) unlock(); sync(); },
    bonus(on) { bonus = on; },
    setLevel(key, value) {
      if (!(key in levels) || !Number.isFinite(value)) return;
      levels[key] = Math.max(0, Math.min(1, value)); save(); unlock(); sync();
    },
    level(key) { return levels[key]; },
    effects() { return muted || document.hidden ? 0 : levels.effects; }
  };
})();
