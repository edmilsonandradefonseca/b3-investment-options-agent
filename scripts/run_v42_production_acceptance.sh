#!/usr/bin/env bash
set -euo pipefail

repo=/opt/b3-investment-options-agent
ticker="${1:-PETR4}"
year="${2:-$(date +%Y)}"

cd "$repo"

echo "===== V4.2 PRODUCTION ACCEPTANCE ====="
echo "branch=$(git branch --show-current)"
echo "commit=$(git rev-parse HEAD)"
echo "ticker=$ticker year=$year"
echo

echo "===== GATE A: PUBLIC CVM OFFICIAL SOURCES ON PRODUCTION HOST ====="
B3_AGENT_PROJECT_ROOT="$repo" \
B3_AGENT_DATA_DIR=/opt/b3-runtime/data \
"$repo/.venv/bin/python" "$repo/scripts/validate_v42_official_sources.py" \
  --ticker "$ticker" --year "$year"

echo
echo "===== GATE B: V4.2 20-STOCK LIVE PILOT ====="
bash "$repo/scripts/run_intelligence_pilot_20.sh" 20

echo
echo "===== GATE B SUMMARY ====="
"$repo/.venv/bin/python" "$repo/scripts/summarize_intelligence_pilot_20.py" \
  --root /opt/b3-runtime/data/derived/intelligence_pilot_v42

echo
echo "===== GATE C: REAL OFFICIAL FATO RELEVANTE REPLAY ====="
bash "$repo/scripts/run_v42_official_replay.sh" "$ticker" "$year"

echo
echo "===== ACCEPTANCE ARTIFACTS ====="
echo "/opt/b3-runtime/data/derived/intelligence_pilot_v42/latest.json"
echo "/opt/b3-runtime/data/derived/v42_historical_replay/latest.json"
echo
echo "GATES A-C: PASS"
echo "Gate D (CVM RAD live) remains a separate credential-dependent gate."
