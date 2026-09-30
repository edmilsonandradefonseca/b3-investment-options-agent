#!/usr/bin/env bash
set -u

REPO="${B3_REPO:-/opt/b3-investment-options-agent}"
UNIT="b3-v43-continuous-acceptance-$(date +%s)"

cd "${REPO}" || exit 2

echo "===== V4.3 CONTINUOUS INTELLIGENCE PRODUCTION ACCEPTANCE ====="
echo "branch=$(git branch --show-current)"
echo "commit=$(git rev-parse HEAD)"
echo

bash -n scripts/run_continuous_intelligence.sh || exit 2
bash -n scripts/install_continuous_intelligence_timers.sh || exit 2

sudo systemd-run   --unit="${UNIT}"   --wait --pipe --collect   -p "User=$(id -un)"   -p "WorkingDirectory=${REPO}"   -p "EnvironmentFile=-/opt/joao-runtime/joao.env"   -p "EnvironmentFile=-/etc/b3-runtime.env"   -p "EnvironmentFile=-/opt/b3-runtime/b3.env"   -p "Environment=B3_AGENT_PROJECT_ROOT=${REPO}"   -p "Environment=B3_AGENT_DATA_DIR=/opt/b3-runtime/data"   -p "Environment=B3_AGENT_TIMEZONE=America/Sao_Paulo"   -p "Environment=LOCAL_REASONING_LOCK_PATH=/var/lock/local-reasoning.lock"   -p "TimeoutStartSec=20min"   "${REPO}/.venv/bin/python"   "${REPO}/scripts/validate_v43_continuous_runtime.py"

rc=$?

echo
echo "V43_CONTINUOUS_RC=${rc}"
if [[ "${rc}" -eq 0 ]]; then
  echo "V4_3_CONTINUOUS_ACCEPTANCE=PASS"
else
  echo "V4_3_CONTINUOUS_ACCEPTANCE=FAIL"
fi
exit "${rc}"
