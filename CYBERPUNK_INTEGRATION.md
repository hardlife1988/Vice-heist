# Vice Heist — Cyberpunk frontend integration

This build is a **static demo only**, not a Stake Engine-approved or RGS-connected game.

- Maps the existing math IDs W/S/B/G/D/R/E/C/P/H to prototype artwork without changing any payout definitions.
- Adds images and sample WAV effects to both `static/` and `dist/`.
- Keeps other unused concept symbols as extras, **not** additional payable symbols.
- Replaces unverified RTP and max-win badges with explicit demo labels.
- All prototype artwork retains dark backgrounds; final production art still needs separate clean transparent renders.
- Browser testing, audio format conversion, full math verification, and RGS integration remain outstanding.
- `static/` is source; `dist/` is the packaged static demo. Verify your build pipeline preserves the assets.

Suggested next actions: run local static server for `dist/`; check mobile image loading; audit math and replace local weighted sampling with RGS events before submission.
