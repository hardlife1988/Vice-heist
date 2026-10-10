# Vice Heist

5 reels, 3 rows and 20 paylines. The always-visible payout chart and detailed rules read the same paytable as the math generator. Stake sessions use the RGS wallet; local demonstration play uses weighted precomputed outcomes and demo chips.

## Run locally

```
python -m pip install -r requirements.txt
python math/build_stake_bundle.py
python server.py
```

Open http://localhost:5000. A clean checkout requires the build: large generated books and lookup tables are CI artifacts, not committed source. `static/` is the frontend source; `dist/` is the packaged demo. `--frontend-only` copies frontend edits while preserving already-generated math.

## Production candidate and validation

See [DEPLOYMENT.md](DEPLOYMENT.md) for release, exhaustive evaluator audit, four-million-round tests, official SDK checks and submission steps. `--release` generates 100,000 outcomes for each mode and a static frontend requiring a Stake session. Base costs 1×; Bonus Buy costs 100× the ordinary bet. Both published distributions target 96% RTP. Maximum cumulative win is 10,000× and terminates the round.

Wallet values use integer micro-units (six decimal places). Currency comes from authentication. Bet limits and selectable levels come from the platform. Bonus purchases require confirmation. Active rounds resume through recorded event checkpoints; failed wager requests are never retried automatically. Public replay uses no wallet requests.

Checks run on the feature branch, with Python unit tests, wallet contracts, real Chromium browser tests, every published event, the actual pinned SDK format verifier and 104 million weighted round samples. Inspect the Actions results for the specific commit before using an artifact. Successful local tests do not constitute platform approval or a verified live-money integration. Publisher session validation and Stake review remain required.

```
python -m unittest discover -s tests -v
node tests/rgs_contract.cjs
node tests/browser_smoke.cjs
node tests/browser_rgs.cjs
```

Browser tests require Playwright and Chromium (`npx playwright install chromium`). The supported local server serves static assets only; Stake RGS performs real wagering and settlement. Legacy independent reel simulation is a diagnostic, not the published RGS distribution.
