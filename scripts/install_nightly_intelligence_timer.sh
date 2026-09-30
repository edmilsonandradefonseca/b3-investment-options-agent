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

sudo tee /etc/systemd/system/b3-nightly-intelligence.service >/dev/null <<EOF
[Unit]
Description=B3 V4.3 nightly Evidence acquisition and enqueue
After=network-online.target ollama.service
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO}
Environment=B3_AGENT_PROJECT_ROOT=${REPO}
Environment=B3_AGENT_TIMEZONE=America/Sao_Paulo
Environment=B3_NIGHTLY_MAX_LOCAL_ANALYSIS_ENQUEUES=5
EnvironmentFile=-${SHARED_ENV_FILE}
EnvironmentFile=-${RUNTIME_ENV_FILE}
EnvironmentFile=-${RUNTIME_ENV_FILE_2}
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

sudo tee /etc/systemd/system/b3-local-evidence-analyst.service >/dev/null <<EOF
[Unit]
Description=B3 V4.3 asynchronous local Evidence analyst
After=network-online.target ollama.service b3-nightly-intelligence.service
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
ExecStart=${REPO}/.venv/bin/python ${REPO}/scripts/run_local_evidence_analyst.py --limit 5
Nice=15
CPUWeight=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=45min
EOF

sudo tee /etc/systemd/system/b3-local-evidence-analyst.timer >/dev/null <<'EOF'
[Unit]
Description=Run B3 V4.3 local Evidence analyst after nightly acquisition

[Timer]
OnCalendar=Mon..Fri *-*-* 22:15:00 America/Sao_Paulo
Persistent=true
AccuracySec=1min
Unit=b3-local-evidence-analyst.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now b3-nightly-intelligence.timer
sudo systemctl enable --now b3-local-evidence-analyst.timer

echo "===== B3 V4.3 NIGHTLY + LOCAL ANALYST TIMERS INSTALLED ====="
echo "shared env:  ${SHARED_ENV_FILE}"
echo "runtime env: ${RUNTIME_ENV_FILE}"
echo "runtime env2:${RUNTIME_ENV_FILE_2}"
systemctl status b3-nightly-intelligence.timer --no-pager
echo
systemctl list-timers b3-nightly-intelligence.timer b3-local-evidence-analyst.timer --no-pager
echo
echo "===== SERVICE ENV FILES ====="
systemctl cat b3-nightly-intelligence.service --no-pager | grep -E 'Environment(File)?='
systemctl cat b3-local-evidence-analyst.service --no-pager | grep -E 'Environment(File)?='
