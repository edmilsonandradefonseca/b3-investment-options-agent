#!/usr/bin/env bash
set -euo pipefail

repo=/opt/b3-investment-options-agent
limit="${1:-20}"
if [[ ! "$limit" =~ ^([1-9]|1[0-9]|20)$ ]]; then
  echo "Usage: bash scripts/run_intelligence_pilot_20.sh [1..20]" >&2
  exit 2
fi

unit="b3-intelligence-pilot-${limit}-$(date +%s)"
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
  -p "TimeoutStartSec=3h" \
  "$repo/.venv/bin/python" "$repo/scripts/intelligence_pilot_20.py" --limit "$limit"

echo "Result: /opt/b3-runtime/data/derived/intelligence_pilot_v42/latest.json"
