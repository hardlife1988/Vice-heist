# Vice Heist: Miami presentation and production math review

This pass adds a restrained Miami noir palette, original 96 BPM procedural music, a more active bonus score, independent persistent music/effects levels, master mute and page visibility handling, a vault transition, reel landing motion and tiered win banners. Reduced motion bypasses decorative sequences. No wager selection, reel rules, payout weights or bet levels were changed.

The procedural score is a first composition for listening and device review, not a mastered studio soundtrack. Actual iPhone/Safari audio and performance still require hands-on verification. Existing effects remain packaged, with a dedicated synthesized button tick. Dist is refreshed from current source, including previously stale RGS fixes already present in static/rgs.js.

## Exact production mathematics

Computed from a deterministic production rebuild with 100,000 outcomes per mode and each outcome's published integer weight. See `validation/volatility_report.json` for input SHA-256 hashes, exact probabilities, category maxima and largest outcome IDs. Multipliers below refer to the ordinary total bet. Probabilities describe the published book distribution, including explicit rare tail scenarios; they are not independent reel-RNG probabilities.

| Metric | Base | Bonus buy |
| --- | ---: | ---: |
| Cost | 1x | 100x |
| Exact return relative to cost | 95.99999890% | 95.99999996% |
| Round hit rate (any positive payout) | 55.9978% | 99.99897% |
| Mean complete-round payout | 0.9600x | 96.0000x |
| Median complete-round payout | 0.1x | 63.2x |
| Mean initial base-spin payout, excluding free spins | 0.82306x | n/a |
| Mean positive initial base-spin win | 1.46981x | n/a |
| Natural free-spin trigger probability | 0.694996% (1 in 143.886) | Guaranteed by purchase |
| Mean free-spin-only payout conditional on natural trigger | 19.70366x | n/a |
| Median free-spin-only payout conditional on natural trigger | 10.2x | n/a |
| Return below purchase/wager cost | 84.0933% | 72.4054% |
| Return exactly purchase/wager cost | 1.1552% | 0.0880% |
| Return above purchase/wager cost | 14.7515% | 27.5066% |
| Standard deviation, ordinary-bet multiples | 17.37759x | 103.53892x |
| Standard deviation divided by cost | 17.37759 | 1.035389 |
| Observed maximum in published distribution | 10,000x | 10,000x |

The initial base-spin hit rate equals the whole-round hit rate in this distribution: natural triggers already pay a scatter win. Hit rate does not mean a profitable round. Most base hits are below the wager. Natural free-spin payout excludes the triggering base spin; purchased bonuses use a different distribution and cost 100x.

| At least this payout | Base probability | Bonus-buy probability |
| --- | ---: | ---: |
| 100x | 0.00690775% (~1 in 14,476) | 27.5946% (~1 in 3.62) |
| 500x | 0.00044000% (~1 in 227,273) | 1.01066% (~1 in 98.95) |
| 1,000x | 0.00043000% (~1 in 232,558) | 0.0385964% (~1 in 2,591) |
| 10,000x | 0.00020000% (~1 in 500,000) | 0.00020000% (~1 in 500,000) |

## Assessment and next math decision

The base game combines frequent small returns with rare extreme payouts; its complete-round variance is dominated by the bonus/tail outcomes. The 10,000x outcomes alone supply approximately 2.08% of the base game's expected payout. A single volatility label would hide the difference between the initial base spin, natural bonuses and purchased bonuses.

The largest outcomes come from deliberately constructed rare tail books, using repeated full-screen Wild or Safe boards. Every board is evaluator-verified, and the cumulative cap can end the feature after four or eight free spins. This is valid for the published weighted-book model, but the visual rhythm and abrupt cap ending need replay review. The unconstructed base free-spin books top out at 384.6x in this finite release; all base outcomes at 500x and above are in the explicit tail set.

The purchased-bonus average of 96x against a 100x cost is consistent with the configured 96% RTP. Its 63.2x median and 72.41% below-cost rate explain why the typical purchase can feel considerably weaker than the average. Natural bonuses have a much lower median (10.2x ordinary bet), with a long upper tail.

Recommended next math experiment: generate candidate distributions that move some very large-win probability into midrange bonus wins, compare median, lower-decile return, 100x break-even probability, RTP, maximum-win attainability and variance side by side. Any candidate must preserve 96% RTP and the 10,000x cap and pass full production verification before replacing this baseline. Changing the median necessarily changes other probabilities; no promised session returns or invented target odds should be advertised.

## Verification boundaries

`analyze_volatility.py` checks every production outcome against its lookup row, reconciles summed paid spin events and final win, enforces cap bounds on cumulative and free-spin totals, and confirms cap markers. The separate `validate_bundle.py` reconstructs every reveal and evaluates its actual paylines and scatters. `stress_published.py` samples 104 million weighted wagering rounds across both modes and all 13 bet sizes.

Local verification passed: nine Python unit tests, twelve payout tests, the RGS/crypto contract suite, the audio lifecycle test, exhaustive evaluator audit of 200,000 production outcomes, 104-million weighted wagering rounds, and independent package verification. Updated browser tests remain unexecuted: the local Chromium download failed and automatic approval review blocked the feature-branch push. The remote feature head remains 0389ca3; main remains 17e5127. Full CI is required for the final commit. Authorized Stake staging remains unexecuted; see `../STAKE_STAGING_ACCEPTANCE.md`. Mock tests and format checks do not establish Stake acceptance. Main, publication and submission are outside this change.
