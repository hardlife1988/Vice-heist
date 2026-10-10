# Vice Heist — Cyberpunk frontend integration

This build is a **static demo**, with no Stake RGS connection or Stake approval.

- Maps the existing math IDs W/S/B/G/D/R/E/C/P/H to prototype artwork without changing payout definitions.
- Keeps unused concept symbols as extra artwork, not additional payable symbols.
- Uses prototype images and sample WAV effects. The artwork retains dark backgrounds; production art still needs clean transparent renders.
- `static/` is the frontend source. `dist/` is the packaged demo, including the full `assets/` tree and the JSON books, lookup CSVs, and `game_config.json` needed at runtime.

Repackage visual changes with `python math/build_stake_bundle.py --frontend-only`. The command copies frontend files and assets recursively, fails clearly when required source inputs are missing, and preserves existing math files. A clean full bundle requires `python math/build_stake_bundle.py`, which intentionally regenerates math too.

Read-only validation of the existing committed 4,000 base and 1,200 bonus books reports **95.8205% base RTP** and **95.9938% bonus-buy RTP** including the 100× cost. Both meet the validator's local tolerance. This does not constitute a full math audit, certification, or production approval.

Automated Chromium checks cover desktop and 320px mobile layouts, artwork loading, base wins/losses, natural free spins, bonus buys, balances, controls, and unavailable or invalid game data. Audio lifecycle checks cover stopping samples on mute and synthesized fallback when sample playback fails. Normal and Turbo animations were also checked separately. These checks do not establish Safari/iOS audio compatibility or final artwork quality.

Further work includes real-device audio compatibility checks/conversion, final artwork, a complete math audit, and Stake RGS integration. Run `python -m http.server 5000 --directory dist` to preview the complete demo. Replace local weighted sampling and demo balance controls with the RGS lifecycle before production submission.
