#!/usr/bin/env bash
set -euo pipefail

REPO="${B3_REPO:-/opt/b3-investment-options-agent}"
UNIT="b3-v43-identity-finalize-$(date +%s)"

cd "${REPO}"

echo "===== V4.3 IDENTITY HARDENING ====="
echo "branch=$(git branch --show-current)"
echo "commit=$(git rev-parse HEAD)"

sudo systemd-run \
  --unit="${UNIT}" \
  --wait --pipe --collect \
  -p "User=$(id -un)" \
  -p "WorkingDirectory=${REPO}" \
  -p "EnvironmentFile=-/etc/b3-runtime.env" \
  -p "EnvironmentFile=-/opt/b3-runtime/b3.env" \
  -p "Environment=B3_AGENT_PROJECT_ROOT=${REPO}" \
  -p "Environment=B3_AGENT_DATA_DIR=/opt/b3-runtime/data" \
  -p "Environment=B3_AGENT_TIMEZONE=America/Sao_Paulo" \
  -p "TimeoutStartSec=10min" \
  "${REPO}/.venv/bin/python" \
  "${REPO}/scripts/validate_v43_identity_runtime.py"

sudo systemctl restart b3-runtime.service
[[ "$(systemctl is-active b3-runtime.service)" == "active" ]]

valid_code="$(curl -sS -o /tmp/b3-v43-valid.json -w '%{http_code}' \
  http://127.0.0.1:8000/intelligence/local/PETR4)"
invalid_code="$(curl -sS -o /tmp/b3-v43-invalid.json -w '%{http_code}' \
  http://127.0.0.1:8000/intelligence/local/1)"

echo "PETR4_HTTP=${valid_code}"
echo "PSEUDO_TICKER_1_HTTP=${invalid_code}"

rm -f /tmp/b3-v43-valid.json /tmp/b3-v43-invalid.json

[[ "${valid_code}" == "200" ]]
[[ "${invalid_code}" == "400" ]]

echo "V4_3_IDENTITY_RUNTIME=PASS"
