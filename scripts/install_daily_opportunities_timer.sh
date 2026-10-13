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

sudo tee /etc/systemd/system/b3-opportunities-daily.service >/dev/null <<EOF
[Unit]
Description=B3 daily evidence-complete Opportunities review
After=network-online.target b3-runtime.service
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO}
Environment=B3_AGENT_PROJECT_ROOT=${REPO}
Environment=B3_AGENT_TIMEZONE=America/Sao_Paulo
EnvironmentFile=-${SHARED_ENV_FILE}
EnvironmentFile=-${RUNTIME_ENV_FILE}
EnvironmentFile=-${RUNTIME_ENV_FILE_2}
ExecStart=${REPO}/.venv/bin/python ${REPO}/scripts/run_daily_opportunities.py
Nice=10
CPUWeight=20
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=90min
EOF

sudo tee /etc/systemd/system/b3-opportunities-daily.timer >/dev/null <<'EOF'
[Unit]
Description=Run complete B3 Opportunities review at midday on weekdays

[Timer]
OnCalendar=Mon..Fri *-*-* 12:00:00 America/Sao_Paulo
Persistent=true
AccuracySec=1min
Unit=b3-opportunities-daily.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now b3-opportunities-daily.timer

echo "===== DAILY B3 OPPORTUNITIES REVIEW TIMER INSTALLED ====="
systemctl status b3-opportunities-daily.timer --no-pager
systemctl list-timers b3-opportunities-daily.timer --no-pager
systemctl cat b3-opportunities-daily.service --no-pager | grep -E 'Environment(File)?='
