#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Building Stake math books + static dist/"
python3 -m pip install -q zstandard 2>/dev/null || true
python3 math/build_stake_bundle.py
echo
echo "Frontend (local demo): dist/"
echo "Math (Stake ACP):      math/library/publish_files/"
ls -lh dist math/library/publish_files
