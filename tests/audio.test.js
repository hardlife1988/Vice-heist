'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('score requires a gesture, preserves levels, and stops for mute/hidden pages', async () => {
  const listeners = {}, timers = new Map(), voices = [], saved = new Map();
  let context, timerId = 0;
  class AudioContext {
    constructor() { context = this; this.currentTime = 0; this.state = 'suspended'; this.destination = {}; }
    createGain() { return { gain: { value: 0, setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {}, setTargetAtTime() {} }, connect() {}, disconnect() {} }; }
    createOscillator() {
      const voice = { frequency: {}, connect() {}, disconnect() {}, start() { this.started = true; }, stop(time) { if (time === undefined) this.cancelled = true; } };
      voices.push(voice); return voice;
    }
    resume() { this.state = 'running'; return Promise.resolve(); }
    suspend() { this.state = 'suspended'; return Promise.resolve(); }
  }
  const document = { hidden: false, addEventListener: (key, fn) => { listeners[key] = fn; } };
  const window = { AudioContext, addEventListener: (key, fn) => { listeners[key] = fn; } };
  const environment = { window, document, localStorage: { getItem: key => saved.get(key), setItem: (key, value) => saved.set(key, value) }, setInterval: fn => { timers.set(++timerId, fn); return timerId; }, clearInterval: id => timers.delete(id) };
  vm.runInNewContext(fs.readFileSync('static/audio.js', 'utf8'), environment);
  const audio = window.HeistAudio;
  assert.equal(voices.length, 0, 'Loading does not autoplay');
  audio.unlock(); await Promise.resolve();
  assert.ok(voices.some(voice => voice.started));
  assert.equal(timers.size, 1);
  audio.mute(true);
  assert.equal(timers.size, 0);
  assert.ok(voices.every(voice => voice.cancelled));
  assert.equal(audio.effects(), 0);
  audio.setLevel('effects', .2);
  assert.equal(JSON.parse(saved.get('vice-heist-audio')).effects, .2);
  audio.mute(false); await Promise.resolve();
  assert.equal(audio.effects(), .2);
  assert.equal(timers.size, 1, 'Unmute creates one scheduler');
  document.hidden = true; listeners.visibilitychange();
  assert.equal(timers.size, 0);
  assert.equal(context.state, 'suspended');
  assert.equal(audio.effects(), 0);
  document.hidden = false; listeners.visibilitychange(); await Promise.resolve();
  assert.equal(timers.size, 1);
  audio.setLevel('music', 0);
  assert.equal(timers.size, 0, 'Zero music volume stops scheduling');
  assert.equal(audio.effects(), .2, 'Effect volume remains independent');
  listeners.pagehide();
  assert.equal(timers.size, 0);
});
