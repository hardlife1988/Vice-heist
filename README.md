# Vice Heist

5-reel, 3-row slot. Static Stake Engine package: precomputed books + browser frontend.

## Play it (Windows 10 / Codespaces)

No Python install needed.

1. Open this repo on GitHub
2. **Code → Codespaces → Create codespace on main**
3. Wait, then **Ports → globe on 5000**
4. Do **not** open `127.0.0.1` in Windows Chrome

Rebuild an old Codespace: **Ctrl+Shift+P → Rebuild Container**

Spin, bonus buy, and free spins run from bundled math books. No Flask.

## What to upload to Stake ACP

Read [STAKE_UPLOAD.md](STAKE_UPLOAD.md).

| Folder | Upload as |
|---|---|
| `math/library/publish_files/` | **Math** |
| `dist/index.html` + `style.css` + `game.js` | **Frontend** |

Do **not** upload Flask `server.py`.

## Rebuild books

```bash
python math/build_stake_bundle.py
```

Current equal-weight simulation (4000 base + 1200 bonus):

- Base RTP ≈ 90.5% (free-spin hit rate ≈ 1%)
- Bonus-buy EV ≈ 17× vs 100× cost (not optimized)

Payouts use Stake units: **100 = 1.0× bet**.

## Local static server

```bash
python -m http.server 5000 --directory dist
```
