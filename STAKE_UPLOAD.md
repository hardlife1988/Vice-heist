# Vice Heist — Stake Engine upload

Two different folders. Do not mix them.

## 1. Math (ACP → Files → Import Math)

Upload **everything inside** `math/library/publish_files/`:

- `index.json` (required)
- `lookUpTable_base.csv`
- `lookUpTable_bonus.csv`
- `books_base.jsonl.zst` (or `.jsonl` if zst is missing)
- `books_bonus.jsonl.zst`

`index.json` modes:

| name | cost | what it is |
|---|---|---|
| base | 1.0 | paid spin, may include free spins |
| bonus | 100.0 | bonus buy → 10 free spins at 2× |

Payout values are integers where **100 = 1.0× bet**.

## 2. Frontend (ACP → Files → Import Frontend)

Upload **only these** from `dist/`:

- `index.html`
- `style.css`
- `game.js`

The other `dist/` files (`books_*.json`, lookup CSVs) are for **local / Codespaces demo** so the game can play without Stake’s RGS.

On Stake.com the RGS serves book events from the math files. This frontend currently plays the bundled JSON books so you can test spin / bonus buy / free spins in a browser with no server.

## 3. Do not upload

- `server.py` / Flask
- `dist/main.py` (removed)
- `static/` Flask demo
- Python math source

## Rebuild books

```bash
python math/build_stake_bundle.py
```

Optional: `VICE_HEIST_BASE=10000 VICE_HEIST_BONUS=3000 python math/build_stake_bundle.py`
