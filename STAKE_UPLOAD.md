# Vice Heist — Stake Engine package status

The current frontend is a static demo that samples local lookup tables and reads bundled JSON books. It has no Stake RGS connection and is not Stake-approved. Packaging these files does not make the game ready for a production submission.

## Math package

`math/library/publish_files/` contains the candidate math package:

- `index.json`, which names each mode's events and weights files
- `lookUpTable_base.csv` and `lookUpTable_bonus.csv`
- `books_base.jsonl.zst` and `books_bonus.jsonl.zst`, or the uncompressed `.jsonl` files when those are the filenames referenced by `index.json`
- `math_summary.json` with generated summary measurements

Use the filenames referenced by `index.json` when assembling an ACP math import. Keep the matching lookup tables and event books together.

| Mode | Cost in ordinary bets | Behavior |
|---|---|---|
| base | 1.0 | Paid spin, which may include free spins |
| bonus | 100.0 | Bonus buy with 10 free spins at 2× |

Payout values are integers where **100 = 1.0× ordinary bet**. The existing committed bundle validates at **95.8205% base RTP** and **95.9938% bonus-buy RTP** after accounting for mode cost. These values pass the local validator's 96% target tolerance of ±0.5 percentage points; they are not certification or ACP approval.

## Current frontend demo package

`static/` is the source. Host or share the **complete `dist/` directory**, preserving its relative paths:

- `index.html`, `style.css`, and `game.js`
- The full `assets/` tree for symbols, backgrounds, UI artwork, and audio
- `books_base.json` and `books_bonus.json`
- `lookUpTable_base.csv` and `lookUpTable_bonus.csv`
- `game_config.json`

Uploading only HTML, CSS, and JavaScript leaves the current demo unable to load its books and artwork. The JSON and CSV files are runtime inputs for this implementation, not optional examples.

Before production frontend submission, implement and test Stake's RGS session, play, balance, and round lifecycle, and consume its returned book events. The current local sampling and demo balance controls do not implement that lifecycle. Reassess runtime packaging requirements after that integration is complete.

The static frontend does not need Flask `server.py`, Python math source, or the separate root frontend files to run.

## Repackage or regenerate

To copy frontend edits and all assets while preserving existing math:

```bash
python math/build_stake_bundle.py --frontend-only
```

This does not recreate missing demo books, CSVs, or configuration. To intentionally regenerate the entire bundle, run:

```bash
python math/build_stake_bundle.py
```

Optional book counts: `VICE_HEIST_BASE=10000 VICE_HEIST_BONUS=3000 python math/build_stake_bundle.py`. Regeneration changes the stored outcomes and lookup weights, so validate the resulting bundle before using it:

```bash
python -m unittest discover -s tests -v
python math/validate_bundle.py
```
