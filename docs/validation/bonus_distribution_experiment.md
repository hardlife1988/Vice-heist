# Bonus distribution experiment

Status: analysis only. The published production bundle and lookup table were not changed.

## Method

Compared the exact weighted bonus-buy outcome distribution in the verified `Vice_Heist_Math.zip` package with alternative integer weights over the same 100,000 outcome books. Each candidate keeps the 96% expected return, 100x purchase cost, 10,000x maximum, and explicitly reserved loss, tail, and max-win outcomes. The experiment shifts probability among ordinary outcomes using a two-parameter exponential reweighting of log payout and the indicator for payouts at or above 100x. Metrics are exact over the weighted outcome books, not Monte Carlo estimates.

## Results

All payout amounts below are multiples of the ordinary bet; the bonus costs 100x.

| Metric | Current verified bundle | Candidate A | Candidate B | Candidate C |
|---|---:|---:|---:|---:|
| Chance of payout above 100x (strict) | 27.5% | 29.9% | 34.9% | 39.8% |
| Chance payout is below the 100x cost | 72.4% | 70.0% | 65.0% | 60.0% |
| Chance payout is at least 100x | 27.6% | 30.0% | 35.0% | 40.0% |
| Mean payout | 96.0x | 96.0x | 96.0x | 96.0x |
| Median payout | 63.2x | 62.8x | 63.0x | 65.0x |
| 90th percentile | 223.0x | 223.0x | 221.6x | 218.4x |
| 99th percentile | 501.2x | 483.8x | 459.8x | 439.8x |
| Standard deviation | 103.54x | 102.02x | 98.80x | 95.43x |
| Chance of at least 500x | 1.0107% | 0.9120% | 0.7282% | 0.5701% |
| Chance of at least 1,000x | 0.03860% | 0.03184% | 0.02133% | 0.01414% |
| Chance of exactly 10,000x | 0.0002% | 0.0002% | 0.0002% | 0.0002% |
| Maximum payout | 10,000x | 10,000x | 10,000x | 10,000x |

Candidate A/B/C target roughly 30%/35%/40% chance of a payout at or above 100x. Due to integer weighting, observed probabilities differ by less than 0.01 percentage point from the target.

## Readout

Candidate C creates more payouts at or above the 100x purchase cost and trims the 500x–1,000x range. It reduces the below-cost rate by 12.4 percentage points while holding the mean at 96% and keeping the 10,000x outcome probability fixed. The median only moves from 63.2x to 65.0x, so most bonuses still return less than their cost. This is a distribution trade-off, not an RTP increase.

The cap outcome remains present at the same probability in these candidates because its reserved weight is unchanged. This experiment checks the published outcome books and weighted distribution; it does not replace an independent RNG review, platform certification, or a fresh full release audit. Do not use candidate weights for submission until they are selected, rebuilt into a complete release package, and all production checks pass.
