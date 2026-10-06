#!/usr/bin/env bash
set -euo pipefail

REPO="${B3_REPO:-/opt/b3-investment-options-agent}"
SERVICE_USER="${SUDO_USER:-${USER}}"
SERVICE_GROUP="$(id -gn "${SERVICE_USER}")"
SHARED_ENV_FILE="${B3_SHARED_PLATFORM_ENV:-/opt/joao-runtime/joao.env}"
RUNTIME_ENV_FILE="${B3_RUNTIME_ENV_FILE:-/etc/b3-runtime.env}"
RUNTIME_ENV_FILE_2="${B3_RUNTIME_ENV_FILE_2:-/opt/b3-runtime/b3.env}"

if [[ ! -x "${REPO}/.venv/bin/python" ]]; then
  echo "Missing Python virtualenv at ${REPO}/.venv/bin/python" >&2
  exit 1
fi
if [[ ! -f "${REPO}/scripts/refresh_market_history.py" ]]; then
  echo "Missing market history refresh script in ${REPO}" >&2
  exit 1
fi

sudo -n tee /etc/systemd/system/b3-market-history-refresh.service >/dev/null <<EOF
[Unit]
Description=B3 official daily OHLCV history refresh
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO}
Environment=B3_AGENT_PROJECT_ROOT=${REPO}
Environment=B3_AGENT_DATA_DIR=/opt/b3-runtime/data
Environment=B3_AGENT_TIMEZONE=America/Sao_Paulo
EnvironmentFile=-${SHARED_ENV_FILE}
EnvironmentFile=-${RUNTIME_ENV_FILE}
EnvironmentFile=-${RUNTIME_ENV_FILE_2}
ExecStart=${REPO}/.venv/bin/python ${REPO}/scripts/refresh_market_history.py
Nice=10
CPUWeight=20
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=45min
EOF

sudo -n tee /etc/systemd/system/b3-market-history-refresh.timer >/dev/null <<'EOF'
[Unit]
Description=Run B3 official OHLCV refresh after the market closes

[Timer]
OnCalendar=Mon..Fri *-*-* 19:30:00 America/Sao_Paulo
Persistent=true
AccuracySec=1min
Unit=b3-market-history-refresh.service

[Install]
WantedBy=timers.target
EOF

sudo -n systemctl daemon-reload
sudo -n systemctl enable --now b3-market-history-refresh.timer
systemctl is-active b3-market-history-refresh.timer
systemctl list-timers b3-market-history-refresh.timer --no-pager
