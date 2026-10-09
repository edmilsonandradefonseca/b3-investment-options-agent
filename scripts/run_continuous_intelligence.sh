#!/usr/bin/env bash
set -euo pipefail

REPO="${B3_REPO:-/opt/b3-investment-options-agent}"
TZ_NAME="${B3_AGENT_TIMEZONE:-America/Sao_Paulo}"
START_HOUR="${B3_INTEL_ACTIVE_START_HOUR:-8}"
END_HOUR="${B3_INTEL_ACTIVE_END_HOUR:-19}"
CONFIG_FILE="${B3_AGENT_DATA_DIR:-/opt/b3-runtime/data}/structured/collection_schedule.json"

read -r START_TIME END_TIME INTERVAL_MINUTES < <("${REPO}/.venv/bin/python" - "${CONFIG_FILE}" "${START_HOUR}" "${END_HOUR}" <<'PY'
import json
import re
import sys
from pathlib import Path

def hour(value):
    return f"{int(value):02d}:00"

start, end, interval = hour(sys.argv[2]), hour(sys.argv[3]), 15
try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    candidate_start, candidate_end = payload["start_time"], payload["end_time"]
    candidate_interval = int(payload.get("interval_minutes", 15))
    valid = all(re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) for value in (candidate_start, candidate_end))
    if valid and candidate_start < candidate_end and candidate_interval in (15, 30, 60):
        start, end, interval = candidate_start, candidate_end, candidate_interval
except (OSError, ValueError, KeyError, TypeError):
    pass
print(start, end, interval)
PY
)

weekday="$(TZ="${TZ_NAME}" date +%u)"
current_time="$(TZ="${TZ_NAME}" date +%H:%M)"
current_hour="${current_time%%:*}"
current_minute="${current_time##*:}"
start_hour="${START_TIME%%:*}"
start_minute="${START_TIME##*:}"
end_hour="${END_TIME%%:*}"
end_minute="${END_TIME##*:}"
current_minutes=$((10#${current_hour} * 60 + 10#${current_minute}))
start_minutes=$((10#${start_hour} * 60 + 10#${start_minute}))
end_minutes=$((10#${end_hour} * 60 + 10#${end_minute}))

if (( weekday > 5 || current_minutes < start_minutes || current_minutes >= end_minutes )); then
  echo "continuous_intelligence=SKIP_OUTSIDE_ACTIVE_WINDOW weekday=${weekday} time=${current_time} window=${START_TIME}-${END_TIME}"
  exit 0
fi

if (( current_minutes % INTERVAL_MINUTES != 0 )); then
  echo "continuous_intelligence=SKIP_INTERVAL time=${current_time} interval_minutes=${INTERVAL_MINUTES}"
  exit 0
fi

exec "${REPO}/.venv/bin/python" "${REPO}/scripts/run_continuous_intelligence.py"
