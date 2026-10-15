# Vice Heist development priorities

Owner direction recorded 2026-10-12: improve the math feel first, then the art
and animation, then live integration. A green technical pipeline is not a
finished commercial game or Stake approval.

## Parallel team and file ownership

| Role | Responsibility |
| --- | --- |
| Product lead | Coordinate decisions, assign shared files, integrate verified work |
| Math engineer | Distribution experiments, feature decisions, books, LUTs, event validation |
| Frontend developer | Controls, animation, rules, responsive layouts, audio integration |
| Visual designer | Consistent symbol/background/UI artwork and manifest |
| Integration engineer | RGS lifecycle, integer wallet precision, recovery and settlement |
| QA/release engineer | Tests, CI evidence, security review, reproducible independent packages |

All development remains on `feature/cyberpunk-assets`. Assign one owner before
editing shared files. Do not merge into main, deploy, or submit without explicit
owner approval.

## First: math and player experience

- Build on the existing [A/B/C bonus distribution analysis](validation/bonus_distribution_experiment.md).
  It is an analysis-only comparison; its candidate weights are not production
  weights. Add a reproducible runner, hashed input provenance and isolated
  candidate tables before treating its reported improvements as release options.
- Compare the exact current distribution against experiments that move RTP
  contribution from 5,000–10,000× outcomes into more frequent 50–300× feature
  outcomes. Keep 96% RTP per mode and the 10,000× round cap.
- Report weighted medians, hit rates, natural feature frequency, feature and
  bonus-buy return distributions, probabilities of recovering the 100× purchase
  cost, tail RTP contribution, and cap probability. Distinguish ordinary-bet
  multipliers from returns divided by bonus-buy cost.
- Choose a coherent volatility target based on these comparisons; do not treat
  a simulated average return as a measure of typical player experience.
- Decide retriggers, expanding Safe/BOOK, and a further free-spin mechanic
  explicitly. Implemented math, event schema, frontend rules, and tests must
  agree. Remove obsolete feature promises if intentionally omitted.
- Revalidate all changed books, exact RTP, SDK formats, payout units, and
  wager-size precision before replacing candidate packages.

## Second: art, animation and UX

Lock a single Miami/cyberpunk heist visual identity. Replace prototype symbols
with consistent transparent high-resolution assets; review frames, HUD, logo,
backgrounds, transitions and tiered celebrations together. Keep math symbol IDs
stable unless a coordinated math change requires otherwise. Unused concept art
does not automatically become a payable symbol.

Verify staggered stops, Turbo, loading/error/recovery states, accurate rules and
paytable, mobile/tablet/desktop layouts, safe areas, and reduced motion against
current code. Never add misleading near-miss boards or alter server outcomes
for presentation. Real iOS/Safari audio and performance require device evidence.

## Third: live integration and release review

Use authorized Stake staging to verify authentication, all supported bet levels,
bonus buys, crypto precision, insufficient funds, interrupted requests, session
recovery, settlement, replay and failures. Mock RGS tests and pinned SDK format
checks remain distinct from live interoperability and platform acceptance.

Review secrets, CSP/hosting, dependencies and server-authoritative payouts.
Produce matching math and frontend ZIPs from the same source commit only after
the relevant checks pass. Keep demo/free-play clearly separated from RGS mode.

## Evidence discipline

The supplied critique is a prioritization input, not proof of the current
repository state. Recheck each assertion against source and test evidence. Some
controls, animations, payout-unit fixes and recovery behavior already exist;
prototype art and unverified live/device operation remain genuine limitations.
Do not describe pending experiments or unexecuted tests as completed.
