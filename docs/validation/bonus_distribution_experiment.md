# Bonus distribution experiment

Status: analysis only. The published production bundle and lookup table were not changed.

## Method

Compared the exact weighted bonus-buy outcome distribution in the verified `Vice_Heist_Math.zip` package with alternative integer weights over the same 100,000 outcome books. Each candidate keeps the 96% expected return, 100x purchase cost, 10,000x maximum, and explicitly reserved loss, tail, and max-win outcomes. The experiment shifts probability among ordinary outcomes using a two-parameter exponential reweighting of `log1p(payout_x)` and the indicator for payouts at or above 100x. Metrics are exact over the weighted outcome books, not Monte Carlo estimates.

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

## Reproduction verified on 2026-10-12

The original A/B/C findings were reproduced using the production inputs identified
by all four SHA-256 hashes in `docs/validation/volatility_report.json`. The runner
rejects mismatched sources, preserves every reserved loss/tail/max-win integer
weight and total weight, and writes candidate lookup tables outside production:

```bash
python math/experiment_bonus_distribution.py
python -m unittest discover -s tests -p test_bonus_experiment.py -v
```

Inputs must first exist in `release/math/` and match the verified baseline report.
The default output is `release/experiments/bonus_distribution/`: `report.json`,
plus candidate A/B/C bonus lookup tables and manifests. These are **analysis
artifacts**, not independently uploadable math packages. They reference the
unchanged hashed outcome books. The runner verifies production input hashes
again after generation. The tracked exact results are in
[`bonus_distribution_report.json`](bonus_distribution_report.json).

The scalar solver fixes ordinary >=100x group mass to each recovery target, then
bisects the log1p tilt to obtain the required mean after subtracting reserved
outcomes. Deterministic largest-remainder rounding preserves integer mass exactly.
The accepted RTP tolerance is `1e-6` in return-ratio units; the measured integer
RTPs were A 95.9999999221%, B 96.0000000871%, C 96.0000000856%.

### Additional exact payout bands

All band boundaries are inclusive. Probability uses the relevant round or
conditional-feature denominator; return share uses paid amounts, not book counts.

| Metric | Baseline bonus | A | B | C |
| --- | ---: | ---: | ---: | ---: |
| Probability of 50–300x payout | 57.3838% | 56.4427% | 55.2279% | 54.9279% |
| Share of return from 50–300x | 66.0656% | 67.1502% | 69.7558% | 72.7348% |
| Probability of 5,000–10,000x payout | 0.000350% | 0.000350% | 0.000350% | 0.000350% |
| Mean return supplied by 5,000–10,000x | 0.030782x | 0.030782x | 0.030782x | 0.030782x |

A/B/C increases cost recovery and the return allocated to the medium band, but
**reduces the chance of a 50–300x payout**. It does not meet the new request for
more frequent payouts in that entire band, and leaves extreme-tail probability
unchanged. Extreme bonus outcomes supply only 0.0321% of baseline bonus return;
removing them alone offers little redistribution budget. Do not describe these
candidates as a completed player-experience redesign.

### Separate natural-feature baseline

Natural-feature probability remains 0.694996% (about one in 144 base rounds).
Conditional free-spin mean is 19.7037x, median 10.2x, and probability of a
50–300x free-spin payout is 2.71483%. Conditional 5,000–10,000x free-spin payouts
occur with probability 0.0503600% and supply 22.4756% of conditional feature
return. Full-round 5,000–10,000x payouts supply 3.20677% of overall base return.
This distinction explains why tail reallocation has more scope to affect natural
features than bonus buys.

A controlled future natural-feature experiment can restrict changes to triggered
books sharing a 2x initial base award, conserving trigger odds and the base-spin
payout distribution. This pool has 487 books: 18 with 50–300x free-spin payouts,
26 with extreme full-round payouts, and 434 with free-spin payouts below 50x.
The A/B/C runner measures pool availability without changing natural weights.
The separate controlled natural-feature experiment below now tests that pool.

### Validation scope

Candidate generation checks integer mass, positive weights, expected RTP,
recovery targets, reserved probabilities, and unchanged 10,000x maximum. Two
independent runs produced byte-identical candidate LUTs, manifests, and reports.
The five experiment regression tests passed. The previously verified book/event
content is reused unchanged; no new SDK approval or live-platform verification
is claimed. A selected candidate still requires complete release regeneration,
exhaustive event audits, SDK-format checks, and wagering-precision simulations.


## Controlled natural-feature tail transfer (2026-10-12)

Run the separate experiment; it neither regenerates nor replaces bonus A/B/C:

```bash
python math/experiment_natural_distribution.py
python -m unittest discover -s tests -p test_natural_experiment.py -v
```

Output: `release/experiments/natural_distribution/`, containing isolated N25/N50/N75
base lookup tables, manifests and `report.json`. The tracked exact report is
[`natural_distribution_report.json`](natural_distribution_report.json). These
remain analysis artifacts referencing the unchanged verified base event book.

The eligible pool consists solely of triggered books with a 2x initial base award.
Donors are the **15 noncap** books whose full-round payout is at least 5,000x;
the 11 exact 10,000x cap books remain unchanged. Medium recipients are the
18 books paying 50–300x in free spins; the balancing pool contains 434 books
paying below 50x in free spins. N25/N50/N75 remove 25%/50%/75% of eligible
noncap donor weight. Their scope does not include all extreme outcomes, because
cap probability is explicitly preserved.

Removed donor mass and return determine added medium mass and removed low mass
by a three-group mass/mean balance. Largest-remainder apportionment uses exact
integer products and divisions. A final mass-neutral transfer between two low
outcomes repairs the integer weighted-payout difference exactly. The runner
fails if a pool is missing, balancing exhausts positive weights, or the exact
return repair is infeasible; it never broadens the pool.

### Exact conditional free-spin results

The probabilities below are **conditional on a natural feature triggering**,
not per base spin. Payouts are ordinary-bet multiples and exclude the initial award.

| Metric | Baseline | N25 | N50 | N75 |
| --- | ---: | ---: | ---: | ---: |
| Chance of 50–300x free-spin payout | 2.7148% | 3.2961% | 3.8774% | 4.4587% |
| Median free-spin payout | 10.2x | 10.2x | 10.2x | 10.2x |
| Mean free-spin payout | 19.7037x | 19.7037x | 19.7037x | 19.7037x |
| 90th percentile | 32.8x | 33.4x | 34.6x | 35.2x |
| 99th percentile | 76.0x | 79.0x | 92.0x | 92.0x |
| Free-spin standard deviation | 204.29x | 197.19x | 189.83x | 182.17x |
| Chance of 5,000–10,000x free-spin payout | 0.050360% | 0.044964% | 0.039569% | 0.034173% |
| Return share from that extreme free-spin band | 22.4756% | 20.5072% | 18.5388% | 16.5704% |

The larger medium frequency is a measured tradeoff against noncap extreme
frequency and low feature outcomes. The conditional median remains 10.2x; this
is a bounded distribution change, not proof of a broadly transformed experience.

### Exact conservation checks

All three candidates preserve **exactly**, using Python-integer comparisons:

- Total LUT weight: 1,000,000,013,254.
- Weighted payout numerator: 96,000,000,174,390 integer payout units times weight.
- Expected base RTP: 95.99999890200601%, identical to baseline and within the 96% tolerance.
- Natural-trigger probability: 0.694995931889%, unchanged.
- Initial base-spin payout distribution, all weights outside the same-award pool,
  and each exact cap-book weight.
- Full-round 10,000x cap probability: 0.0001999999973492%, unchanged.
- Positive integer weights for every outcome, unchanged book IDs and payouts.

Two full production-data runs produced byte-identical candidate lookup tables,
manifests and reports. Five natural-experiment regression tests pass, including
infeasible pool/rounding checks and exact conservation. Original production input
hashes and existing bonus A/B/C lookup hashes remain unchanged. These tests do
not replace full selected-candidate release audits, SDK checks, or simulations.
