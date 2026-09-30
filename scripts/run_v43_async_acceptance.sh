#!/usr/bin/env bash
set -u

repo=/opt/b3-investment-options-agent
stage="${1:-enqueue}"
ticker="${2:-PETR4}"
year="${3:-2026}"
unit="b3-v43-async-${stage,,}-$(date +%s)"

if [[ "$stage" != "enqueue" && "$stage" != "worker" && "$stage" != "context" ]]; then
  echo "usage: $0 {enqueue|worker|context} [TICKER] [YEAR]" >&2
  exit 2
fi

nice_value=10
cpu_weight=20
timeout="20m"
if [[ "$stage" == "worker" ]]; then
  nice_value=15
  cpu_weight=10
  timeout="45m"
fi

sudo systemd-run --unit="$unit" --wait --pipe --collect \
  -p "User=$(id -un)" \
  -p "WorkingDirectory=$repo" \
  -p "EnvironmentFile=-/opt/joao-runtime/joao.env" \
  -p "EnvironmentFile=-/etc/b3-runtime.env" \
  -p "EnvironmentFile=-/opt/b3-runtime/b3.env" \
  -p "Environment=B3_AGENT_PROJECT_ROOT=$repo" \
  -p "Environment=B3_AGENT_DATA_DIR=/opt/b3-runtime/data" \
  -p "Nice=$nice_value" \
  -p "CPUWeight=$cpu_weight" \
  -p "TimeoutStartSec=$timeout" \
  "$repo/.venv/bin/python" \
  "$repo/scripts/validate_v43_async_pipeline.py" \
  "$stage" --ticker "$ticker" --year "$year"
