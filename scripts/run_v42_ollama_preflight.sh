#!/usr/bin/env bash
set -euo pipefail

repo=/opt/b3-investment-options-agent
unit="b3-v42-ollama-preflight-$(date +%s)"

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
  -p "TimeoutStartSec=5m" \
  "$repo/.venv/bin/python" "$repo/scripts/validate_v42_ollama_runtime.py"
