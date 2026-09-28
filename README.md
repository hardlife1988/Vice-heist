# Vice Heist Cyberpunk — Starter Asset Pack

Prototype images extracted from the approved cyberpunk concept sheet, **not** individually generated transparent production art. Each 512×512 WebP symbol retains its original dark backing. Inspect edge quality and redesign final assets before shipping.

Contents:
- 16 prototype symbol crops, 2 background crops, 2 UI crops
- `asset_manifest.json` (descriptive names, **not** yet mapped to math symbol IDs)
- 7 original synthesized WAV audio sketches; no licensed music
- `effects.css` optional glow/pulse/reduced-motion styles

Integration:
1. Compare `math/paytable.py`, `math/reels/*.csv`, and `static/game.js` to assign symbol IDs.
2. Place assets in the frontend's served static path and update image URLs.
3. Convert/replace WAVs with suitable compressed audio and adjust `static/audio_manifest.json` after testing.
4. Keep Stake math files unchanged until the independent math/RGS audit is complete.
5. Verify artwork, licenses, mobile layout, accessibility, and RGS compatibility before submission.

This is an **asset starter**, not a Stake Engine-compliant game build.
