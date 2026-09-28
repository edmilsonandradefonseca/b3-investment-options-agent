#!/usr/bin/env bash
set -euo pipefail

REPO="${B3_REPO:-/opt/b3-investment-options-agent}"
SERVICE_USER="${SUDO_USER:-${USER}}"
SERVICE_GROUP="$(id -gn "${SERVICE_USER}")"
ENV_FILE="${B3_SHARED_PLATFORM_ENV:-/opt/joao-runtime/joao.env}"

if [[ ! -x "${REPO}/.venv/bin/python" ]]; then
  echo "Missing Python virtualenv at ${REPO}/.venv/bin/python" >&2
  exit 1
fi

sudo tee /etc/systemd/system/b3-nightly-intelligence.service >/dev/null <<EOF
[Unit]
Description=B3 V4.1 nightly intelligence
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO}
Environment=B3_AGENT_PROJECT_ROOT=${REPO}
Environment=B3_AGENT_TIMEZONE=America/Sao_Paulo
Environment=B3_NIGHTLY_MAX_DEEPSEEK_CALLS=5
EnvironmentFile=-${ENV_FILE}
ExecStart=${REPO}/.venv/bin/python ${REPO}/scripts/run_nightly_intelligence.py
Nice=10
CPUWeight=20
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=90min
EOF

sudo tee /etc/systemd/system/b3-nightly-intelligence.timer >/dev/null <<'EOF'
[Unit]
Description=Run B3 nightly intelligence on business weekdays

[Timer]
OnCalendar=Mon..Fri *-*-* 22:00:00 America/Sao_Paulo
Persistent=true
AccuracySec=1min
Unit=b3-nightly-intelligence.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now b3-nightly-intelligence.timer

echo "===== B3 NIGHTLY TIMER INSTALLED ====="
systemctl status b3-nightly-intelligence.timer --no-pager
echo
systemctl list-timers b3-nightly-intelligence.timer --no-pager
