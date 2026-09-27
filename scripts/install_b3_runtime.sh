#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_GROUP="$(id -gn "$TARGET_USER")"
RUNTIME_ROOT="${B3_RUNTIME_ROOT:-/opt/b3-runtime}"
API_HOST="${B3_API_HOST:-127.0.0.1}"
API_PORT="${B3_API_PORT:-8000}"
ENV_FILE="/etc/b3-runtime.env"
SERVICE_FILE="/etc/systemd/system/b3-runtime.service"

cd "$ROOT"

test -x .venv/bin/python || {
  echo "ERROR: $ROOT/.venv/bin/python missing"
  exit 2
}

.venv/bin/python -m pip install -e .

sudo install -d -o "$TARGET_USER" -g "$TARGET_GROUP"   "$RUNTIME_ROOT"   "$RUNTIME_ROOT/data/imports"   "$RUNTIME_ROOT/data/parquet"   "$RUNTIME_ROOT/logs"   "$RUNTIME_ROOT/backups"

sudo tee "$ENV_FILE" >/dev/null <<EOF
B3_RUNTIME_ROOT=$RUNTIME_ROOT
B3_AGENT_PROJECT_ROOT=$ROOT
B3_AGENT_DATA_DIR=$RUNTIME_ROOT/data
B3_AGENT_LOGS_DIR=$RUNTIME_ROOT/logs
B3_API_HOST=$API_HOST
B3_API_PORT=$API_PORT
EOF

sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=B3 Investment & Options Agent Runtime
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$TARGET_USER
Group=$TARGET_GROUP
WorkingDirectory=$ROOT
EnvironmentFile=-$ENV_FILE
EnvironmentFile=-$RUNTIME_ROOT/b3.env
ExecStart=$ROOT/.venv/bin/python -m b3_agent.runtime.service
Restart=on-failure
RestartSec=3
KillMode=control-group
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
EOF

sudo ln -sf "$ROOT/.venv/bin/b3-runtime" /usr/local/bin/b3-runtime
sudo systemctl daemon-reload
sudo systemctl enable b3-runtime.service

echo "Installed b3-runtime"
echo "service: $SERVICE_FILE"
echo "env:     $ENV_FILE"
echo "secrets: $RUNTIME_ROOT/b3.env (if present)"
echo "cli:     /usr/local/bin/b3-runtime"
echo "bind:    $API_HOST:$API_PORT"
echo
echo "Start with: b3-runtime start"
echo "Check with: b3-runtime status"
