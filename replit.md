# Vice Heist Slot Game

A 5-reel, 3-row video slot game built for the **Stake Engine** platform, running as a Flask web app on Replit.

## Stack
- **Backend**: Python / Flask (`server.py`)
- **Math engine**: `math/` — reel engine, win evaluator, provably fair RNG
- **Frontend**: Vanilla HTML/CSS/JS (`index.html`, `style.css`, `game.js`)

## How to run
```bash
python server.py
```
The server listens on port 5000. The workflow is configured to start it automatically.

## Game features
- 5 reels × 3 rows, **20 paylines**
- **Provably fair** spins: HMAC-SHA256(server\_seed, client\_seed:nonce) — Stake Engine standard
- **Free Spins**: 3+ Scatters anywhere → 10 free spins at 2× multiplier
- **Bonus Buy**: 100× bet to instantly trigger Free Spins
- **Wild** substitutes all non-scatter symbols
- Max win: **10,000× bet** | RTP target: **96%**

## API endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config` | Game config + session state |
| POST | `/api/spin` | `{bet, bonus_buy}` → spin result |
| POST | `/api/seed` | `{client_seed}` → rotate server seed |
| POST | `/api/verify` | `{server_seed, client_seed, nonce, reel_grid}` → verify spin |
| POST | `/api/deposit` | `{amount}` → add demo balance |

## Provably fair flow
1. Server generates a random `server_seed` and shows its **SHA-256 hash** to the player before any bets.
2. Player sets a `client_seed` (editable in the UI).
3. Each spin: `HMAC-SHA256(key=server_seed, msg=f"{client_seed}:{nonce}")` → 32 bytes of entropy.
4. 15 symbol picks (5 reels × 3 rows) use 2 bytes each (30 bytes total, fits in one hash).
5. When the player changes their client seed, the old `server_seed` is **revealed** for audit.

## Project structure
```
server.py          # Flask backend (entry point)
index.html         # Game UI
game.js            # Frontend logic
style.css          # Styles
math/
  game_config.py   # Game parameters
  reel_engine.py   # Provably fair reel spinning
  win_evaluator.py # 20-payline win evaluation
  paytable.py      # Symbol pays & payline definitions
  stake_engine.py  # Provably fair helpers & verification
  gamestate.py     # Session state tracker
dist/              # Static export for Stake Engine ACP upload
requirements.txt   # Flask
```

## User preferences
- Keep the existing project structure (Python math engine + vanilla JS frontend)
- Stake Engine compliant provably fair RNG is a hard requirement
