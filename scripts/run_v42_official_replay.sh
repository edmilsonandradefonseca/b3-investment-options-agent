#!/usr/bin/env bash
set -euo pipefail

repo=/opt/b3-investment-options-agent
ticker="${1:-PETR4}"
year="${2:-$(date +%Y)}"

if [[ ! "$ticker" =~ ^[A-Za-z0-9]+$ ]]; then
  echo "Invalid ticker: $ticker" >&2
  exit 2
fi
if [[ ! "$year" =~ ^20[0-9]{2}$ ]]; then
  echo "Invalid year: $year" >&2
  exit 2
fi

unit="b3-v42-official-replay-${ticker,,}-$(date +%s)"

sudo systemd-run --unit="$unit" --wait --pipe --collect \
  -p "User=$(id -un)" \
  -p "WorkingDirectory=$repo" \
  -p "EnvironmentFile=-/opt/joao-runtime/joao.env" \
  -p "EnvironmentFile=-/etc/b3-runtime.env" \
  -p "EnvironmentFile=-/opt/b3-runtime/b3.env" \
  -p "Environment=B3_AGENT_PROJECT_ROOT=$repo" \
  -p "Environment=B3_AGENT_DATA_DIR=/opt/b3-runtime/data" \
  -p "Nice=10" \
  -p "CPUWeight=20" \
  -p "TimeoutStartSec=30m" \
  "$repo/.venv/bin/python" "$repo/scripts/replay_v42_official_fact.py" \
  --ticker "$ticker" --year "$year"

echo "Result: /opt/b3-runtime/data/derived/v42_historical_replay/latest.json"
