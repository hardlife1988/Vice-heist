#!/bin/bash
set -euo pipefail
echo "Building Vice Heist frontend + Stake-style math files..."
cd "$(dirname "$0")"
python3 math/build_stake_bundle.py
echo "Done. Frontend is in dist/. Math files are in math/library/publish_files/"
ls -la dist math/library/publish_files
