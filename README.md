# Vice Heist

5-reel, 3-row slot prototype with precomputed math books and a static browser demo. The frontend samples local lookup tables and plays bundled book events. It is not connected to Stake's RGS and is not an approved production game.

## Play locally

Serve the complete `dist/` directory over HTTP:

```bash
python -m http.server 5000 --directory dist
```

Open `http://localhost:5000` in a local browser. Spin, bonus buy, and free spins run from bundled books without Flask. Opening `index.html` directly as a file does not provide the HTTP requests needed to load the books.

For Windows 10 / Codespaces, select the branch containing the work you want to preview, then **Code → Codespaces → Create codespace**. Wait for startup and open the forwarded port 5000 from the **Ports** tab. To update an older Codespace's container configuration, use **Ctrl+Shift+P → Rebuild Container**.

## Frontend source and packaging

`static/` contains the frontend source and prototype image/audio assets. `dist/` is the packaged demo. Repackage frontend edits without changing any existing math books or lookup weights:

```bash
python math/build_stake_bundle.py --frontend-only
```

This copies `index.html`, `style.css`, `game.js`, and the full `assets/` tree from `static/`. It requires those source files and the assets directory; missing inputs fail with their paths. It does not regenerate or restore math files.

Keep all of these together when hosting or sharing the current demo:

- `index.html`, `style.css`, and `game.js`
- The complete `assets/` tree, including symbols, backgrounds, UI artwork, and audio
- `books_base.json` and `books_bonus.json`
- `lookUpTable_base.csv` and `lookUpTable_bonus.csv`
- `game_config.json`

If rebuilding a clean checkout's entire bundle, or intentionally generating new math, run:

```bash
python math/build_stake_bundle.py
```

That command regenerates math publish files, demo books, lookup tables, and configuration, then packages the frontend. Use `--frontend-only` for visual changes to preserve the committed math bundle.

## Validate the existing math bundle

These checks do not regenerate math:

```bash
python -m unittest discover -s tests -v
python math/validate_bundle.py
```

The existing committed bundle contains 4,000 base books and 1,200 bonus books. Validation computes weighted RTP of **95.8205% base** and **95.9938% bonus buy**, accounting for the 100× bonus-buy cost. Both pass the validator's 96% target tolerance of ±0.5 percentage points. Payout units are **100 = 1.0× ordinary bet**.

These are checks of the stored books, lookup weights, and final payout events. They do not certify all game math, fairness, production readiness, or Stake acceptance.

## Browser checks

The demo includes working Turbo, sound mute, and Game Info controls. The WIN display shows the latest round, and both bet displays stay synchronized. Spin and Bonus Buy remain disabled until the books and lookup tables load and match.

Run the browser regression checks with Node.js 22+, Python, and Playwright:

```bash
npm install --no-save --package-lock=false playwright@1.62.1
npx --no-install playwright install chromium
node tests/browser_smoke.cjs
```

The script starts and stops its own local server. It checks deterministic base wins/losses, free spins, bonus buys, balances, controls, loading failures, and mobile artwork/layout. Set `CHROMIUM_PATH` to use an existing Chromium executable or `PYTHON` to select Python. The GitHub validation workflow runs unit tests, a clean bundle build, math validation, and browser checks on relevant pull requests and feature-branch pushes.

See [STAKE_UPLOAD.md](STAKE_UPLOAD.md) for math package contents and the RGS integration required before production submission, and [CYBERPUNK_INTEGRATION.md](CYBERPUNK_INTEGRATION.md) for artwork status.
