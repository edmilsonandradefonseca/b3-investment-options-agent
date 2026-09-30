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

common_env() {
  cat <<EOF
Environment=B3_AGENT_PROJECT_ROOT=${REPO}
Environment=B3_AGENT_TIMEZONE=America/Sao_Paulo
Environment=B3_INTEL_CURSOR_OVERLAP_MINUTES=30
Environment=B3_INTEL_INITIAL_LOOKBACK_HOURS=24
Environment=B3_INTEL_ACTIVE_START_HOUR=8
Environment=B3_INTEL_ACTIVE_END_HOUR=19
EnvironmentFile=-${SHARED_ENV_FILE}
EnvironmentFile=-${RUNTIME_ENV_FILE}
EnvironmentFile=-${RUNTIME_ENV_FILE_2}
EOF
}

sudo tee /etc/systemd/system/b3-continuous-intelligence.service >/dev/null <<EOF
[Unit]
Description=B3 V4.3 continuous CVM discovery
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO}
$(common_env)
ExecStart=${REPO}/scripts/run_continuous_intelligence.sh
Nice=5
CPUWeight=30
TimeoutStartSec=10min
EOF

sudo tee /etc/systemd/system/b3-continuous-intelligence.timer >/dev/null <<'EOF'
[Unit]
Description=Poll CVM Download Multiplo every 15 minutes

[Timer]
OnCalendar=Mon..Fri *-*-* *:00/15:00
Persistent=true
AccuracySec=1min
Unit=b3-continuous-intelligence.service

[Install]
WantedBy=timers.target
EOF

sudo tee /etc/systemd/system/b3-local-relevance-screen.service >/dev/null <<EOF
[Unit]
Description=B3 V4.3 local relevance screen
After=ollama.service
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO}
$(common_env)
ExecStart=${REPO}/.venv/bin/python ${REPO}/scripts/run_local_relevance_screen.py --limit 5
Nice=15
CPUWeight=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=30min
EOF

sudo tee /etc/systemd/system/b3-local-relevance-screen.timer >/dev/null <<'EOF'
[Unit]
Description=Drain B3 relevance queue after discovery

[Timer]
OnCalendar=Mon..Fri *-*-* *:05/15:00
Persistent=true
AccuracySec=1min
Unit=b3-local-relevance-screen.service

[Install]
WantedBy=timers.target
EOF

sudo tee /etc/systemd/system/b3-local-evidence-analyst.service >/dev/null <<EOF
[Unit]
Description=B3 V4.3 asynchronous local Evidence dossier analyst
After=ollama.service
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO}
$(common_env)
ExecStart=${REPO}/.venv/bin/python ${REPO}/scripts/run_local_evidence_analyst.py --limit 5
Nice=15
CPUWeight=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=45min
EOF

sudo tee /etc/systemd/system/b3-local-evidence-analyst.timer >/dev/null <<'EOF'
[Unit]
Description=Drain B3 dossier queue after relevance screening

[Timer]
OnCalendar=Mon..Fri *-*-* *:10/15:00
Persistent=true
AccuracySec=1min
Unit=b3-local-evidence-analyst.service

[Install]
WantedBy=timers.target
EOF

sudo tee /etc/systemd/system/b3-cvm-reconciliation.service >/dev/null <<EOF
[Unit]
Description=B3 daily CVM Open Data reconciliation
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO}
$(common_env)
ExecStart=${REPO}/.venv/bin/python ${REPO}/scripts/run_cvm_reconciliation.py
Nice=10
CPUWeight=20
TimeoutStartSec=30min
EOF

sudo tee /etc/systemd/system/b3-cvm-reconciliation.timer >/dev/null <<'EOF'
[Unit]
Description=Daily B3 CVM Open Data reconciliation

[Timer]
OnCalendar=Mon..Fri *-*-* 20:30:00 America/Sao_Paulo
Persistent=true
AccuracySec=5min
Unit=b3-cvm-reconciliation.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now   b3-continuous-intelligence.timer   b3-local-relevance-screen.timer   b3-local-evidence-analyst.timer   b3-cvm-reconciliation.timer

systemctl list-timers   b3-continuous-intelligence.timer   b3-local-relevance-screen.timer   b3-local-evidence-analyst.timer   b3-cvm-reconciliation.timer   --no-pager
