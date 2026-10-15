# Vice Heist — Production handoff and Stake submission readiness

> Status: **candidate packages validated by automated CI; NOT certified, approved, deployed, or submitted to Stake.**
> Source branch: `feature/cyberpunk-assets`. **Do not merge into `main`, deploy, or submit without explicit owner approval.**

## Evidence (2026-10-10)

- [Successful CI run #25](https://github.com/hardlife1988/Vice-heist/actions/runs/38063152354) built and audited production books, ran browser smoke/RGS tests, validated SDK formats, and passed 104,000,000 simulated wagering rounds (4,000,000 per 13 bet levels per base/bonus mode).
- The run uploaded the `vice-heist-calibrated-math` Actions artifact. Download from the run's Artifacts section and retain its SHA-256 digest and the CI logs for review.
- SDK checks are **format checks against a pinned SDK revision**, not Stake certification. Tests use a mock RGS; live Stake wallet/session interoperability is **not yet demonstrated**.
- RTP target: 96% for each mode; integer `payoutMultiplier` convention: **100 units = 1.0× ordinary bet**. Bonus buy costs 100× the selected ordinary bet. Maximum round payout is 10,000× ordinary bet.
- `math/stress_published.py` records per-mode/bet observed RTP, winning rounds, cap hits, standard errors, seeds, hashes, and precision checks in `four_million_report.json`. Inspect that file, not just the Actions success badge.

## Generate the two independent release packages

From the repository root on the feature branch:

```bash
python -m pip install -r requirements.txt
python math/build_stake_bundle.py --release
python math/validate_bundle.py --publish release/math --release
python math/stress_published.py --rounds 4000000
python tests/verify_release_packages.py
```

The **math package** is the contents of `release/math/`, including:
- `index.json` identifying each mode's compressed event book and weighted lookup table
- `books_base.jsonl.zst`, `books_bonus.jsonl.zst`
- `lookUpTable_base.csv`, `lookUpTable_bonus.csv`
- `math_summary.json`, `replay_ids.json`, `validation_report.json`, `four_million_report.json`
- `sdk_verification.json` only after running `math/sdk_verify.py --sdk <pinned-sdk-checkout>`

The **frontend package** is the contents of `release/frontend/`, including `index.html`, `style.css`, `game.js`, `money.js`, `rgs.js`, `game_config.json`, and the complete `assets/` tree. Production frontend **must not** include local outcome books or weighted lookup tables. The frontend requests events from the RGS.

Package directories **separately**; do not upload the repository, test suite, or the demo `dist/` as the production frontend. Keep a matching pair generated from the same source commit, with checksums.

## Pre-submission gates still requiring human/platform review

1. Confirm current Stake Engine onboarding and required game/RGS endpoints, event schema, asset hosting, jurisdiction flags, replay contract, and submission format with the platform. SDK-format pass is not an approval.
2. Execute an authorized staging integration against the actual Stake RGS: authentication, supported crypto currencies and precision, 13 bet levels, insufficient funds, bonus buys, interrupted/duplicate requests, recovery, round settlement, replay, and failure handling. Automated tests currently use mock RGS responses.
3. Complete security review: no secrets in frontend, no client-authoritative payouts, no unsafe external URLs, CSP/asset hosting review, and dependency audit. Retain test logs and package hashes.
4. Review [PR #1](https://github.com/hardlife1988/Vice-heist/pull/1) before any proposed merge. **Never merge, deploy, or submit without explicit approval.**

## Important distinction

A green CI run verifies the automated checks exercised on that commit. It does not certify real-money operation or guarantee Stake acceptance. The original `STAKE_UPLOAD.md` was a demo-era note and is superseded by this handoff.

## Final two ZIP files

The full CI release workflow creates `release/Vice_Heist_Math.zip` and `release/Vice_Heist_Frontend.zip`, each containing a separate top-level folder and its own verified `SHA256SUMS.txt`. Download both together from the `vice-heist-stake-upload-zips` GitHub Actions artifact after a **successful** run. These are release candidates until platform staging checks and owner approval are complete. Never submit, deploy, or merge automatically.
