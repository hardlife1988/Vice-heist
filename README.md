# Vice Heist Slot

A **Stake Engine compatible** 5-reel, 3-row video slot game.

## Game Features
- 20 paylines
- Free Spins (3+ Scatters)
- Bonus Vault Pick Feature
- Wild symbols
- Max Win: **10,000x**
- RTP: **96%**

## Run on Windows 10 (GitHub Codespaces)

You do **not** need to install Python. Codespaces runs in your browser.

1. Open [hardlife1988/Vice-heist](https://github.com/hardlife1988/Vice-heist)
2. Click the green **Code** button
3. Open the **Codespaces** tab
4. Click **Create codespace on main** (or **Rebuild container** if you already have one open)
5. Wait until the bottom status says Flask / pip is done
6. When it asks about port **5000**, click **Open in Browser**

The game starts automatically (`python server.py`).

If you already had an old Codespace open, it will still be broken until you rebuild:
**Ctrl+Shift+P** → type **Rebuild Container** → Enter.

## Files for Stake
- `dist/` folder contains all static files needed for upload.

## How to Test
Open `dist/index.html` in browser, or use Codespaces as above.

## Deployment
1. Upload `dist/` contents to Stake Engine ACP.
2. Math simulation files are in `math/`.

Ready for review!
