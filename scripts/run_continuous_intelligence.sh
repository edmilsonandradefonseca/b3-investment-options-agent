#!/usr/bin/env bash
set -euo pipefail

REPO="${B3_REPO:-/opt/b3-investment-options-agent}"
TZ_NAME="${B3_AGENT_TIMEZONE:-America/Sao_Paulo}"
START_HOUR="${B3_INTEL_ACTIVE_START_HOUR:-8}"
END_HOUR="${B3_INTEL_ACTIVE_END_HOUR:-19}"

weekday="$(TZ="${TZ_NAME}" date +%u)"
hour="$(TZ="${TZ_NAME}" date +%H)"
hour=$((10#${hour}))

if (( weekday > 5 || hour < START_HOUR || hour >= END_HOUR )); then
  echo "continuous_intelligence=SKIP_OUTSIDE_ACTIVE_WINDOW weekday=${weekday} hour=${hour}"
  exit 0
fi

exec "${REPO}/.venv/bin/python" "${REPO}/scripts/run_continuous_intelligence.py"
