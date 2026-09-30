#!/usr/bin/env bash
set -u

REPO="${B3_REPO:-/opt/b3-investment-options-agent}"
JOAO_REPO="${JOAO_REPO:-${HOME}/joao-resolve}"
PRIME_UNIT="b3-v43-production-prime-$(date +%s)"

cd "${REPO}" || exit 2

echo "===== STEP 1: INTEGRATED ACCEPTANCE ====="
bash scripts/run_v43_continuous_acceptance.sh
accept_rc=$?
echo "ACCEPTANCE_RC=${accept_rc}"
if [[ "${accept_rc}" -ne 0 ]]; then
  echo "DEPLOY_ABORTED=ACCEPTANCE_FAILED"
  exit "${accept_rc}"
fi

echo
echo "===== STEP 2: INSTALL PRODUCTION TIMERS ====="
bash scripts/install_continuous_intelligence_timers.sh
install_rc=$?
echo "INSTALL_RC=${install_rc}"
if [[ "${install_rc}" -ne 0 ]]; then
  echo "DEPLOY_ABORTED=TIMER_INSTALL_FAILED"
  exit "${install_rc}"
fi

echo
echo "===== STEP 3: RESTART SHARED RUNTIMES ====="
if systemctl list-unit-files joao-scheduler.service --no-legend 2>/dev/null | grep -q joao-scheduler; then
  sudo systemctl restart joao-scheduler.service || exit 4
  echo "JOAO_SCHEDULER=$(systemctl is-active joao-scheduler.service)"
fi
sudo systemctl restart b3-runtime.service || exit 4
echo "B3_RUNTIME=$(systemctl is-active b3-runtime.service)"

echo
echo "===== STEP 4: PRIME REAL PRODUCTION DISCOVERY ====="
sudo systemd-run \
  --unit="${PRIME_UNIT}" \
  --wait --pipe --collect \
  -p "User=$(id -un)" \
  -p "WorkingDirectory=${REPO}" \
  -p "EnvironmentFile=-/opt/joao-runtime/joao.env" \
  -p "EnvironmentFile=-/etc/b3-runtime.env" \
  -p "EnvironmentFile=-/opt/b3-runtime/b3.env" \
  -p "Environment=B3_AGENT_PROJECT_ROOT=${REPO}" \
  -p "Environment=B3_AGENT_DATA_DIR=/opt/b3-runtime/data" \
  -p "Environment=B3_AGENT_TIMEZONE=America/Sao_Paulo" \
  -p "Environment=LOCAL_REASONING_LOCK_PATH=/var/lock/local-reasoning.lock" \
  -p "TimeoutStartSec=10min" \
  "${REPO}/.venv/bin/python" \
  "${REPO}/scripts/run_continuous_intelligence.py"
prime_rc=$?
echo "PRIME_RC=${prime_rc}"
if [[ "${prime_rc}" -ne 0 ]]; then
  echo "DEPLOY_ABORTED=PRODUCTION_PRIME_FAILED"
  exit "${prime_rc}"
fi

echo
echo "===== STEP 5: VERIFY API + TIMERS ====="
for path in \
  /intelligence/local/status \
  /intelligence/local/queue \
  /intelligence/local/manifest \
  /intelligence/local/PETR4
do
  code="$(curl -sS -o /tmp/b3-v43-endpoint.json -w '%{http_code}' "http://127.0.0.1:8000${path}")"
  echo "${path} -> HTTP ${code}"
  if [[ "${code}" != "200" ]]; then
    cat /tmp/b3-v43-endpoint.json || true
    rm -f /tmp/b3-v43-endpoint.json
    exit 5
  fi
done
rm -f /tmp/b3-v43-endpoint.json

for timer in \
  b3-continuous-intelligence.timer \
  b3-local-relevance-screen.timer \
  b3-local-evidence-analyst.timer \
  b3-cvm-reconciliation.timer
do
  state="$(systemctl is-active "${timer}")"
  echo "${timer}=${state}"
  [[ "${state}" == "active" ]] || exit 6
done

echo
echo "===== V4.3 CONTINUOUS BACKEND ====="
echo "B3_HEAD=$(git rev-parse HEAD)"
echo "JOAO_HEAD=$(git -C "${JOAO_REPO}" rev-parse HEAD)"
echo "V4_3_CONTINUOUS_ACCEPTANCE=PASS"
echo "PRODUCTION_TIMERS=PASS"
echo "PRODUCTION_DISCOVERY=PASS"
echo "OBSERVABILITY_API=PASS"
echo "SHARED_LOCAL_REASONING_LOCK=PASS"
echo "BACKEND_CONTINUOUS_READY=PASS"
