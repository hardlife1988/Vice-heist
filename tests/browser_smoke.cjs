#!/usr/bin/env node
'use strict';

// Run after packaging dist/: node tests/browser_smoke.cjs
// Requires Playwright and a Chromium browser. CHROMIUM_PATH can override the
// system browser; PYTHON can override the static server's Python executable.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const money = value => Number(value.replace(/[^\d.-]/g, ''));
const roundCash = value => Math.round(value * 100) / 100;
const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

async function freePort() {
  const socket = net.createServer();
  socket.listen(0, '127.0.0.1');
  await once(socket, 'listening');
  const port = socket.address().port;
  await new Promise((resolve, reject) => socket.close(error => error ? reject(error) : resolve()));
  return port;
}

async function waitForServer(url, server, output) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (attempt > 0 && !server.pid) throw new Error(`Could not start the static server: ${output()}`);
    if (server.exitCode !== null) throw new Error(`Static server exited: ${output()}`);
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch (_) {
      // The child process may still be binding its listening socket.
    }
    await delay(100);
  }
  throw new Error(`Static server did not become ready: ${output()}`);
}

async function stopServer(server) {
  if (!server.pid || server.exitCode !== null || server.signalCode !== null) return;
  const exited = once(server, 'exit');
  server.kill('SIGTERM');
  await Promise.race([exited, delay(1000)]);
  if (server.exitCode === null && server.signalCode === null) {
    server.kill('SIGKILL');
    await exited;
  }
}

async function expectReady(page) {
  await page.waitForFunction(() => {
    const spin = document.getElementById('btn-spin');
    const bonus = document.getElementById('btn-bonus-buy');
    return !spin.disabled && !bonus.disabled
      && /ready/i.test(document.getElementById('win-log').textContent);
  }, undefined, { timeout: 20000 });
}

async function cashAt(page, selector) {
  return money(await page.locator(selector).innerText());
}

async function expectNoOverflow(page, width) {
  await page.setViewportSize({ width, height: 900 });
  const layout = await page.evaluate(() => ({
    viewport: innerWidth,
    document: document.documentElement.scrollWidth,
    outside: [...document.querySelectorAll('button, .reels-frame, .control-rail')]
      .filter(element => element.getClientRects().length)
      .map(element => ({
        id: element.id || element.className,
        left: element.getBoundingClientRect().left,
        right: element.getBoundingClientRect().right,
      }))
      .filter(bounds => bounds.left < -0.5 || bounds.right > innerWidth + 0.5),
  }));
  assert.ok(layout.document <= layout.viewport, `${width}px horizontal overflow: ${JSON.stringify(layout)}`);
  assert.deepEqual(layout.outside, [], `${width}px controls extend outside the viewport`);
}

async function decodeReelImages(page) {
  await page.waitForFunction(() => document.querySelectorAll('#reels-grid img').length === 15);
  const results = await page.locator('#reels-grid img').evaluateAll(async images => {
    return Promise.all(images.map(async image => {
      await image.decode();
      return { src: image.getAttribute('src'), width: image.naturalWidth, height: image.naturalHeight };
    }));
  });
  assert.ok(results.every(image => image.width > 0 && image.height > 0), 'Reel artwork must decode');
}

async function selectRealBook(page, mode, kind) {
  return page.evaluate(async ({ mode, kind }) => {
    if (!window.__smokeBooks) {
      const [baseBooks, bonusBooks, baseText, bonusText] = await Promise.all([
        fetch('books_base.json').then(response => response.json()),
        fetch('books_bonus.json').then(response => response.json()),
        fetch('lookUpTable_base.csv').then(response => response.text()),
        fetch('lookUpTable_bonus.csv').then(response => response.text()),
      ]);
      const parseLut = text => text.trim().split(/\r?\n/).filter(Boolean).map(line => {
        const [id, weight, payout] = line.split(',').map(Number);
        return { id, weight, payout };
      });
      window.__smokeBooks = {
        base: { books: baseBooks, lut: parseLut(baseText) },
        bonus: { books: bonusBooks, lut: parseLut(bonusText) },
      };
    }
    const { books, lut } = window.__smokeBooks[mode];
    const book = books.find(candidate => {
      const weighted = lut.some(row => row.id === candidate.id && row.weight > 0);
      const feature = candidate.events.some(event => event.type === 'freeSpinTrigger');
      if (!weighted) return false;
      if (kind === 'free-spins') return feature && candidate.payoutMultiplier > 0;
      if (kind === 'loss') return !feature && candidate.payoutMultiplier === 0;
      return candidate.payoutMultiplier > 0 && (mode === 'bonus' || !feature);
    });
    if (!book) throw new Error(`No weighted ${mode} ${kind} book in packaged data`);
    const total = lut.reduce((sum, row) => sum + row.weight, 0);
    let preceding = 0;
    let selectedRow;
    for (const row of lut) {
      if (row.id === book.id) { selectedRow = row; break; }
      preceding += row.weight;
    }
    // Use the midpoint of this real lookup row's interval. Temporary reel
    // animation cannot change the already selected game's payout.
    Math.random = () => (preceding + selectedRow.weight / 2) / total;
    const reveals = book.events.filter(event => event.type === 'reveal');
    const finalBoard = reveals.at(-1).board;
    const freeSpinEvents = book.events.filter(event => event.type === 'updateFreeSpin').length;
    window.__smokeSawFreeSpins = false;
    window.__smokeFreeSpinUpdates = [];
    window.__smokeFeatureObserver?.disconnect();
    window.__smokeFeatureObserver = new MutationObserver(() => {
      const bar = document.getElementById('free-spins-bar');
      if (getComputedStyle(bar).display !== 'none') window.__smokeSawFreeSpins = true;
      const counter = document.getElementById('fs-count').textContent.trim();
      if (counter) window.__smokeFreeSpinUpdates.push(counter);
    });
    window.__smokeFeatureObserver.observe(document.getElementById('free-spins-bar'), {
      attributes: true, subtree: true, childList: true, characterData: true,
    });
    return { id: book.id, payout: book.payoutMultiplier, finalBoard, freeSpinEvents };
  }, { mode, kind });
}

async function playKnownRound(page, mode, kind) {
  const book = await selectRealBook(page, mode, kind);
  const bet = await cashAt(page, '#bet-value');
  const before = await cashAt(page, '#balance');
  const payout = roundCash(book.payout / 100 * bet);
  await page.locator(mode === 'bonus' ? '#btn-bonus-buy' : '#btn-spin').click();
  await page.waitForFunction(() => !document.getElementById('btn-spin').disabled, undefined, { timeout: 20000 });
  assert.equal(await cashAt(page, '#balance'), roundCash(before - bet * (mode === 'bonus' ? 100 : 1) + payout), `${mode} book ${book.id} balance`);
  assert.equal(await cashAt(page, '#total-win'), payout, `${mode} book ${book.id} current-round win`);
  assert.equal(await page.locator('#btn-spin .spin-arrow').count(), 1, 'Spin arrow survives round replay');
  assert.equal(await page.locator('#btn-spin .spin-text').innerText(), 'SPIN');
  assert.equal(await page.locator('#free-spins-bar').isVisible(), false, 'Free-spin status closes after settlement');
  const actualBoard = await page.evaluate(() => Array.from({ length: 5 }, (_, reel) =>
    Array.from({ length: 3 }, (_, row) => document.getElementById(`cell-${row}-${reel}`).dataset.sym)));
  assert.deepEqual(actualBoard, book.finalBoard.map(column => column.map(symbol => typeof symbol === 'string' ? symbol : symbol.name)), 'Displayed final board matches selected book');
  if (kind === 'loss') assert.match(await page.locator('#win-log').innerText(), /no win/i);
  if (book.freeSpinEvents) {
    const feature = await page.evaluate(() => ({ saw: window.__smokeSawFreeSpins, updates: window.__smokeFreeSpinUpdates }));
    assert.equal(feature.saw, true, `${mode} feature status becomes visible`);
    assert.ok(new Set(feature.updates).size >= book.freeSpinEvents, `${mode} feature counter advances through every free spin`);
  }
  await decodeReelImages(page);
  console.log(`PASS ${mode} ${kind} book ${book.id}: bet $${bet.toFixed(2)}, payout $${payout.toFixed(2)}`);
}

async function main() {
  assert.ok(fs.existsSync(path.join(root, 'dist', 'books_base.json')), 'Build the static dist/ package before running browser checks');
  const port = await freePort();
  const url = `http://127.0.0.1:${port}/`;
  const server = spawn(process.env.PYTHON || 'python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1', '--directory', 'dist'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
  let serverOutput = '';
  for (const stream of [server.stdout, server.stderr]) stream.on('data', chunk => { serverOutput = (serverOutput + chunk).slice(-4000); });
  server.on('error', error => { serverOutput += error.message; });
  let browser;
  try {
    await waitForServer(url, server, () => serverOutput);
    const executablePath = process.env.CHROMIUM_PATH || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
    browser = await chromium.launch({ executablePath, headless: true, args: ['--no-sandbox'] });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce' });
    // External fonts and the browser's optional favicon probe are unrelated to
    // gameplay. Serve empty successes so their availability adds no noise.
    await context.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, route => route.fulfill({ status: 200, contentType: 'text/css', body: '' }));
    await context.route('**/favicon.ico', route => route.fulfill({ status: 204, body: '' }));
    const page = await context.newPage();
    const pageErrors = [];
    const consoleErrors = [];
    const failedAssets = [];
    const assetResponses = new Set();
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    page.on('response', response => {
      if (response.url().startsWith(url + 'assets/')) {
        if (!response.ok()) failedAssets.push(`${response.status()} ${response.url()}`);
        else assetResponses.add(new URL(response.url()).pathname);
      }
    });
    page.on('requestfailed', request => {
      if (request.url().startsWith(url + 'assets/')) failedAssets.push(request.url());
    });
    let releaseBooks;
    const heldBooks = new Promise(resolve => { releaseBooks = resolve; });
    await page.route('**/books_base.json', async route => { await heldBooks; await route.continue(); });
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    assert.equal(await page.locator('#btn-spin').isDisabled(), true, 'Spin is disabled while books load');
    assert.equal(await page.locator('#btn-bonus-buy').isDisabled(), true, 'Bonus buy is disabled while books load');
    releaseBooks();
    await expectReady(page);
    await page.unroute('**/books_base.json');
    console.log('PASS loading disables wagers until the packaged books are ready');

    await page.locator('#bet-up').click();
    assert.equal(await cashAt(page, '#bet-value'), 2);
    assert.equal(await cashAt(page, '#hud-bet-value'), 2, 'Both bet displays stay synchronized');
    assert.equal(await cashAt(page, '#bonus-cost'), 200, 'Bonus price tracks bet');
    await page.locator('#btn-turbo').click();
    assert.equal(await page.locator('#btn-turbo').getAttribute('aria-pressed'), 'true');
    assert.ok((await page.locator('#btn-turbo').getAttribute('class')).split(/\s+/).includes('active'));
    await page.locator('#btn-turbo').click();
    assert.equal(await page.locator('#btn-turbo').getAttribute('aria-pressed'), 'false');
    const infoWasHidden = await page.locator('#info-panel').evaluate(element => element.hidden);
    await page.locator('#btn-menu').click();
    assert.equal(await page.locator('#info-panel').evaluate(element => element.hidden), !infoWasHidden);
    assert.equal(await page.locator('#btn-menu').getAttribute('aria-expanded'), String(infoWasHidden));
    await page.locator('#btn-menu').click();
    assert.equal(await page.locator('#info-panel').evaluate(element => element.hidden), infoWasHidden);
    const beforeMute = await cashAt(page, '#balance');
    await page.locator('#btn-mute').focus();
    await page.keyboard.press('Space');
    assert.equal(await page.locator('#btn-mute').getAttribute('aria-pressed'), 'true', 'Space activates focused mute');
    assert.equal(await cashAt(page, '#balance'), beforeMute, 'Native keyboard controls never place a wager');
    assert.equal(await page.locator('#btn-spin').isDisabled(), false);
    console.log('PASS bet, turbo, information menu and keyboard mute controls');

    await expectNoOverflow(page, 320);
    await playKnownRound(page, 'base', 'win');
    await expectNoOverflow(page, 1280);
    await playKnownRound(page, 'base', 'loss');
    await playKnownRound(page, 'base', 'free-spins');
    await playKnownRound(page, 'bonus', 'win');
    assert.ok(assetResponses.has('/assets/backgrounds/city_concept.webp'), 'Packaged city artwork is requested');
    assert.ok([...assetResponses].some(asset => asset.startsWith('/assets/symbols/')), 'Packaged symbol artwork is requested');
    assert.deepEqual(failedAssets, [], 'All requested local assets return successfully');
    assert.deepEqual(pageErrors, [], 'Happy-path browser execution has no uncaught errors');
    assert.deepEqual(consoleErrors, [], 'Happy-path browser execution has no console errors');
    console.log('PASS 320px/desktop layout, artwork decoding and asset delivery');

    // These controlled media stubs verify lifecycle behavior, not whether a
    // particular device can produce audible output from the packaged samples.
    const audioPage = await context.newPage();
    const audioPageErrors = [];
    audioPage.on('pageerror', error => audioPageErrors.push(error.message));
    await audioPage.addInitScript(() => {
      window.__smokeAudio = { plays: 0, pauses: 0, oscillators: 0 };
      HTMLMediaElement.prototype.play = function () {
        window.__smokeAudio.plays += 1;
        return Promise.resolve();
      };
      const realPause = HTMLMediaElement.prototype.pause;
      HTMLMediaElement.prototype.pause = function () {
        window.__smokeAudio.pauses += 1;
        return realPause.call(this);
      };
    });
    await audioPage.goto(url, { waitUntil: 'domcontentloaded' });
    await expectReady(audioPage);
    assert.equal(await audioPage.locator('#btn-mute').getAttribute('aria-pressed'), 'false');
    await audioPage.locator('#btn-deposit').click();
    assert.ok(await audioPage.evaluate(() => window.__smokeAudio.plays > 0), 'Demo deposit starts a sample voice');
    await audioPage.locator('#btn-mute').click();
    assert.equal(await audioPage.locator('#btn-mute').getAttribute('aria-pressed'), 'true');
    assert.ok(await audioPage.evaluate(() => window.__smokeAudio.pauses > 0), 'Mute pauses an existing sample voice');
    await audioPage.locator('#btn-mute').click();
    assert.equal(await audioPage.locator('#btn-mute').getAttribute('aria-pressed'), 'false');
    await audioPage.evaluate(() => {
      HTMLMediaElement.prototype.play = function () {
        return Promise.reject(new Error('Intentional sample playback failure'));
      };
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) throw new Error('This browser does not expose Web Audio');
      const realCreateOscillator = AudioContextClass.prototype.createOscillator;
      AudioContextClass.prototype.createOscillator = function () {
        window.__smokeAudio.oscillators += 1;
        return realCreateOscillator.call(this);
      };
    });
    await audioPage.locator('#btn-deposit').click();
    await audioPage.waitForFunction(() => window.__smokeAudio.oscillators > 0);
    assert.deepEqual(audioPageErrors, [], 'Sample playback rejection is handled without uncaught errors');
    await audioPage.close();
    console.log('PASS audio lifecycle: mute pauses samples and rejected playback starts the tone fallback');

    const failedPage = await context.newPage();
    const failedPageErrors = [];
    failedPage.on('pageerror', error => failedPageErrors.push(error.message));
    await failedPage.route('**/books_base.json', route => route.abort('failed'));
    await failedPage.goto(url, { waitUntil: 'domcontentloaded' });
    await failedPage.waitForFunction(() => /could not|unable|failed|error|reload/i.test(document.getElementById('win-log').textContent));
    assert.equal(await failedPage.locator('#btn-spin').isDisabled(), true, 'Failed book load disables spin');
    assert.equal(await failedPage.locator('#btn-bonus-buy').isDisabled(), true, 'Failed book load disables bonus buy');
    assert.match(await failedPage.locator('#win-log').innerText(), /load|connection|reload|unavailable/i, 'Loading failure gives an actionable explanation');
    assert.equal(await cashAt(failedPage, '#balance'), 1000, 'Loading failure preserves demo chips');
    assert.deepEqual(failedPageErrors, [], 'Loading failure is handled without uncaught browser errors');
    console.log('PASS failed book loading keeps wagers disabled and reports the failure');
    await failedPage.close();

    const malformedPage = await context.newPage();
    const malformedPageErrors = [];
    malformedPage.on('pageerror', error => malformedPageErrors.push(error.message));
    await malformedPage.route('**/lookUpTable_base.csv', async route => {
      const response = await route.fetch();
      const rows = (await response.text()).trim().split(/\r?\n/);
      const first = rows[0].split(',');
      first[1] = '0';
      rows[0] = first.join(',');
      await route.fulfill({ response, status: 200, contentType: 'text/csv', body: rows.join('\n') });
    });
    await malformedPage.goto(url, { waitUntil: 'domcontentloaded' });
    await malformedPage.waitForFunction(() => /could not|unable|failed|error|reload/i.test(document.getElementById('win-log').textContent));
    assert.equal(await malformedPage.locator('#btn-spin').isDisabled(), true, 'Malformed lookup data disables spin');
    assert.equal(await malformedPage.locator('#btn-bonus-buy').isDisabled(), true, 'Malformed lookup data disables bonus buy');
    assert.match(await malformedPage.locator('#win-log').innerText(), /load|reload|unavailable/i, 'Malformed data reports a load error');
    assert.equal(await cashAt(malformedPage, '#balance'), 1000, 'Malformed data preserves demo chips');
    assert.deepEqual(malformedPageErrors, [], 'Malformed lookup data is rejected without uncaught errors');
    await malformedPage.close();
    console.log('PASS malformed HTTP 200 lookup data keeps wagers disabled and preserves balance');
    await context.close();
    console.log('Browser smoke checks passed.');
  } finally {
    try {
      if (browser) await browser.close();
    } finally {
      await stopServer(server);
    }
  }
}

main().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
