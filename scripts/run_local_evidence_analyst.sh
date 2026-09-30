#!/usr/bin/env bash
set -euo pipefail

repo=/opt/b3-investment-options-agent
limit="\${1:-5}"
unit="b3-local-evidence-analyst-$(date +%s)"

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
  -p "TimeoutStartSec=45m" \
  "$repo/.venv/bin/python" "$repo/scripts/run_local_evidence_analyst.py" --limit "$limit"
