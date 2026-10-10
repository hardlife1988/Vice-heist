# Vice Heist release candidate

Work stays on `feature/cyberpunk-assets`. Main is not a release target.

Install `requirements.txt`, then run:

```
python -m unittest discover -s tests -v
node tests/rgs_contract.cjs
python math/build_stake_bundle.py
python math/validate_bundle.py
python math/build_stake_bundle.py --release
python math/validate_bundle.py --publish release/math --release
python math/stress_published.py
```

The release has 100,000 complete outcomes in EACH mode. `stress_published.py` samples the actual published integer lookup weights: four million complete wagering rounds for each of 13 configured demonstration bets in both modes, 104 million total. This is not 104 million fresh reel simulations. Every published event is separately audited against the evaluator, including component awards, caps and feature totals. Rare 10,000× wins cause meaningful sampled RTP variation; exact weighted RTP determines the long-run return. Reports preserve observed results, seeds and sample digests.

Official SDK format checks use revision `a6dccd86de740cc5d318079483cb6204cc5c19bc` of https://github.com/engineio/math-sdk:

```
python math/sdk_verify.py --sdk /path/to/math-sdk
```

Upload `release/math/index.json`, both compressed JSONL book files and lookup CSVs to the publisher math tool. Upload `release/frontend/` as static frontend assets. Reports and diagnostic JSON are evidence, not substitutes for the publisher validation.

The production frontend requires Stake URL parameters `sessionID` and `rgs_url`. It authenticates, uses returned wallet currency and micro-unit bet limits, submits ordinary bet amounts for base and 100× bonus buy modes, records resume checkpoints and settles active rounds. A failed paid request is never automatically retried. Reload recovers through authentication. `replay=true` uses only the public replay endpoint. Demo deposits and local outcome selection are disabled for Stake sessions and excluded from the production math selection flow.

`python server.py` serves the packaged `dist/` demonstration at port 5000, including images, audio and data. It is not a real-money wagering backend.

Before submission: verify the candidate in a real publisher test session for every returned bet level/currency and jurisdiction configuration; upload the math and frontend, and run publisher replay/approval checks. Local format checks and simulations do not certify Stake acceptance. Actual live-session evidence requires a publisher-issued session; none is stored in this repository.
