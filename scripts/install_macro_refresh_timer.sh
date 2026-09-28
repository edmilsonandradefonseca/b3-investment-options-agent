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

if [[ ! -f "${REPO}/scripts/update_macro.py" ]]; then
  echo "Missing ${REPO}/scripts/update_macro.py" >&2
  exit 1
fi

sudo tee /etc/systemd/system/b3-macro-refresh.service >/dev/null <<EOF
[Unit]
Description=B3 Agent daily BCB macro refresh
After=network-online.target
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
ExecStart=${REPO}/.venv/bin/python ${REPO}/scripts/update_macro.py
Nice=10
EOF

sudo tee /etc/systemd/system/b3-macro-refresh.timer >/dev/null <<'EOF'
[Unit]
Description=Run B3 macro refresh on Brazilian business weekdays

[Timer]
OnCalendar=Mon..Fri *-*-* 19:00:00 America/Sao_Paulo
Persistent=true
AccuracySec=1min
Unit=b3-macro-refresh.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now b3-macro-refresh.timer

echo "===== B3 MACRO TIMER INSTALLED ====="
echo "shared env:  ${SHARED_ENV_FILE}"
echo "runtime env: ${RUNTIME_ENV_FILE}"
echo "runtime env2:${RUNTIME_ENV_FILE_2}"
systemctl status b3-macro-refresh.timer --no-pager
echo
systemctl list-timers b3-macro-refresh.timer --no-pager
echo
echo "===== SERVICE ENV FILES ====="
systemctl cat b3-macro-refresh.service --no-pager | grep -E 'Environment(File)?='
