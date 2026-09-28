#!/usr/bin/env bash
set -uo pipefail

ROOT="${B3_REPO:-/opt/b3-investment-options-agent}"
cd "$ROOT" || exit 2

LOG="/tmp/b3-backend-full-validation-$(date +%Y%m%d-%H%M%S).log"
FAILURES=0
WARNINGS=0

exec > >(tee "$LOG") 2>&1

section() {
  echo
  echo "======================================================"
  echo " $1"
  echo "======================================================"
}

pass() { echo "PASS: $*"; }
warn() { echo "WARN: $*"; WARNINGS=$((WARNINGS + 1)); }
fail() { echo "FAIL: $*"; FAILURES=$((FAILURES + 1)); }

run_gate() {
  local name="$1"
  shift
  section "$name"
  if "$@"; then
    pass "$name"
  else
    fail "$name"
  fi
}

pytest_clean_gate() (
  # Unit/regression tests must validate code defaults, not production env overrides.
  while IFS='=' read -r name _; do
    case "$name" in
      B3_AGENT_*|B3_OPENCLAW_*|B3_ALLOW_OPENAI_API_FALLBACK)
        unset "$name"
        ;;
    esac
  done < <(env)

  .venv/bin/python -m pytest -q
)

load_env() {
  set -a
  [[ -r /etc/b3-runtime.env ]] && source /etc/b3-runtime.env
  [[ -r /opt/b3-runtime/b3.env ]] && source /opt/b3-runtime/b3.env
  [[ -r "${B3_SHARED_PLATFORM_ENV:-/opt/joao-runtime/joao.env}" ]] && source "${B3_SHARED_PLATFORM_ENV:-/opt/joao-runtime/joao.env}"
  set +a
  export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
  export B3_ACCEPTANCE_TICKER="${B3_ACCEPTANCE_TICKER:-PETR4}"
  export B3_ACCEPTANCE_TICKERS="${B3_ACCEPTANCE_TICKERS:-PETR4,VALE3,ITUB4,WEGE3,BBAS3}"
}

backend_acceptance_gate() {
  local out="/tmp/b3-backend-acceptance-full-validation.txt"
  if ! .venv/bin/python scripts/backend_acceptance.py >"$out" 2>&1; then
    cat "$out"
    return 1
  fi
  cat "$out"

  local warning_count
  warning_count="$(grep -Ec ' WARNING ' "$out" || true)"
  if [[ "$warning_count" -gt 0 ]]; then
    warn "Backend acceptance emitted $warning_count runtime warning(s); inspect canonical data availability above"
  fi
  return 0
}

uc_acceptance_gate() {
  local out="/tmp/b3-uc-real-acceptance-full-validation.txt"
  if ! .venv/bin/python scripts/uc_real_acceptance.py >"$out" 2>&1; then
    cat "$out"
    return 1
  fi
  cat "$out"

  local limited failed
  limited="$(grep -Ec '^UC-[0-9]+ LIMITED ' "$out" || true)"
  failed="$(grep -Ec '^UC-[0-9]+ FAIL ' "$out" || true)"

  if [[ "$failed" -gt 0 ]]; then
    return 1
  fi
  if [[ "$limited" -gt 0 ]]; then
    warn "UC acceptance has $limited LIMITED use case(s); backend code passed but real-data completeness is not yet full"
  fi

  if grep -Eq '^UC-03 PASS .*rejected=0([[:space:]]|$)' "$out"; then
    warn "UC-03 passes functionally but rejected=0 indicates opportunity filtering/ranking calibration still needs review"
  fi
  return 0
}

http_assertions() {
  local base="${B3_API_URL:-http://127.0.0.1:8000}"

  curl -fsS "$base/health" >/tmp/b3-health-before.json || return 1

  curl -fsS -X POST -H "Content-Type: application/json"     -d '{"task":"Resuma o estado atual da carteira","context":{"client":"backend-full-validation","dashboard_page":"Portfolio","use_cases":["UC-01"]}}'     "$base/orchestrate" >/tmp/b3-fast-uc01.json || return 1

  curl -fsS -X POST -H "Content-Type: application/json"     -d '{"task":"UC-02 Options Position & Lifecycle Intelligence","context":{"client":"backend-full-validation","dashboard_page":"Options","use_cases":["UC-02"]}}'     "$base/orchestrate" >/tmp/b3-fast-uc02.json || return 1

  curl -fsS -X POST -H "Content-Type: application/json"     -d '{"task":"UC-11 Risk, Scenario & Stress Intelligence","context":{"client":"backend-full-validation","dashboard_page":"Risk & Stress","use_cases":["UC-11"]}}'     "$base/orchestrate" >/tmp/b3-fast-uc11-baseline.json || return 1

  curl -fsS -X POST -H "Content-Type: application/json"     -d '{"task":"rode stress PETR4 -10%","context":{"client":"backend-full-validation"}}'     "$base/orchestrate" >/tmp/b3-fast-uc11-stress.json || return 1

  .venv/bin/python - <<'PY'
import json
from pathlib import Path

def load(name):
    return json.loads(Path(name).read_text())

uc01 = load("/tmp/b3-fast-uc01.json")
uc02 = load("/tmp/b3-fast-uc02.json")
uc11b = load("/tmp/b3-fast-uc11-baseline.json")
uc11s = load("/tmp/b3-fast-uc11-stress.json")

assert uc01["status"] == "COMPLETED", uc01
assert uc01["result"]["fast_route"]["target"] == "portfolio_engine", uc01
assert uc01["result"]["fast_route"]["use_case"] == "UC-01", uc01
assert len(uc01["result"]["portfolio_context"]["positions"]) > 0, uc01

assert uc02["status"] == "COMPLETED", uc02
assert uc02["result"]["fast_route"]["target"] == "options_engine", uc02
assert uc02["result"]["fast_route"]["use_case"] == "UC-02", uc02
assert uc02["result"]["option_position_count"] > 0, uc02

assert uc11b["status"] == "LIMITED", uc11b
assert uc11b["result"]["fast_route"]["target"] == "stress_engine", uc11b
assert uc11b["result"]["scenario_result"] is None, uc11b

assert uc11s["status"] == "COMPLETED", uc11s
assert uc11s["result"]["fast_route"]["target"] == "stress_engine", uc11s
stress = uc11s["result"]["scenario_result"]
assert stress["sensitivities"]["ticker:PETR4"] == -0.10, stress
assert stress["position_stress"], stress

print(
    "FAST ROUTER HTTP OK "
    f"UC01_positions={len(uc01['result']['portfolio_context']['positions'])} "
    f"UC02_options={uc02['result']['option_position_count']} "
    f"UC11_pnl={stress['portfolio_pnl']:.2f}"
)
PY
}

local_ai_gate() {
  local ollama="${B3_OLLAMA_URL:-http://127.0.0.1:11434}"
  local model="${B3_LOCAL_REASONING_MODEL:-deepseek-r1:8b}"

  .venv/bin/python - "$ollama" "$model" <<'PY'
import json
import sys
import urllib.request

base=sys.argv[1].rstrip("/")
model=sys.argv[2]

with urllib.request.urlopen(base + "/api/tags", timeout=10) as response:
    tags=json.loads(response.read().decode("utf-8"))

names={str(item.get("name") or "") for item in tags.get("models", [])}
if not any(name == model or name.startswith(model + ":") or model.startswith(name + ":") for name in names):
    raise SystemExit(f"configured local model not found: {model}; installed={sorted(names)}")

payload={
    "model": model,
    "messages":[{"role":"user","content":"Responda somente: DEEPSEEK_RUNTIME_OK"}],
    "stream":False,
    "keep_alive":0,
    "options":{"temperature":0},
}
request=urllib.request.Request(
    base + "/api/chat",
    data=json.dumps(payload).encode(),
    headers={"Content-Type":"application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=300) as response:
    body=json.loads(response.read().decode("utf-8"))
content=str((body.get("message") or {}).get("content") or "").strip()
if "DEEPSEEK_RUNTIME_OK" not in content:
    raise SystemExit(f"unexpected DeepSeek response: {content!r}")
print(f"DEEPSEEK LOCAL OK model={body.get('model') or model}")
PY
}

openclaw_gate() {
  local bin="${B3_OPENCLAW_BIN:-$(command -v openclaw || true)}"
  [[ -n "$bin" && -x "$bin" ]] || { echo "openclaw executable unavailable"; return 1; }

  "$bin" agent     --agent "${B3_OPENCLAW_AGENT:-b3-investment}"     --model "${B3_OPENCLAW_MODEL:-openai/gpt-5.6-luna}"     --session-key b3-backend-full-validation     --message "Responda somente: B3_OPENCLAW_VALIDATION_OK"     | tee /tmp/b3-openclaw-validation.txt

  grep -q "B3_OPENCLAW_VALIDATION_OK" /tmp/b3-openclaw-validation.txt
}

service_checks() {
  if systemctl is-active --quiet b3-runtime.service; then
    pass "b3-runtime.service active"
  else
    fail "b3-runtime.service not active"
  fi

  if systemctl --user is-active --quiet openclaw-gateway.service; then
    pass "openclaw-gateway.service active"
  elif pgrep -af 'openclaw.*gateway' >/dev/null; then
    pass "OpenClaw gateway process active"
  else
    fail "OpenClaw gateway not active"
  fi

  if systemctl is-active --quiet joao-scheduler.service; then
    warn "joao-scheduler.service is active; shared-host local reasoning can contend"
  else
    pass "joao-scheduler.service not active"
  fi

  for timer in b3-macro-refresh.timer b3-nightly-intelligence.timer; do
    if systemctl is-enabled --quiet "$timer" 2>/dev/null; then
      pass "$timer enabled"
      systemctl list-timers "$timer" --no-pager || true
    else
      warn "$timer is not enabled"
    fi
  done
}

log_gate() {
  local since="${VALIDATION_STARTED_AT}"
  local bad
  bad="$(journalctl -u b3-runtime.service --since "$since" --no-pager 2>/dev/null     | grep -Ei '429|insufficient_quota|credit_balance_exhausted|Traceback|ERROR' || true)"
  if [[ -n "$bad" ]]; then
    echo "$bad"
    return 1
  fi
  echo "No 429/quota/Traceback/ERROR in b3-runtime service calls during validation."
}

section "B3 BACKEND FULL VALIDATION"
echo "Started: $(date --iso-8601=seconds)"
echo "Root: $ROOT"
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git log -1 --oneline)"
echo "Log: $LOG"

VALIDATION_STARTED_AT="$(date '+%Y-%m-%d %H:%M:%S')"

run_gate "GATE 1 - FULL PYTEST REGRESSION" \
  pytest_clean_gate

# Production/runtime values are loaded only after code-default regression passes.
load_env

run_gate "GATE 2 - REAL SHARED BACKEND ACCEPTANCE" \
  backend_acceptance_gate

run_gate "GATE 3 - REAL UC01..UC12 ACCEPTANCE" \
  uc_acceptance_gate

run_gate "GATE 4 - FAST ROUTER HTTP E2E"   http_assertions

section "GATE 5 - SERVICES AND TIMERS"
service_checks

run_gate "GATE 6 - DEEPSEEK LOCAL RUNTIME"   local_ai_gate

run_gate "GATE 7 - OPENCLAW/LUNA TRANSPORT"   openclaw_gate

run_gate "GATE 8 - B3 RUNTIME ERROR SCAN"   log_gate

section "FINAL HEALTH"
curl -fsS "${B3_API_URL:-http://127.0.0.1:8000}/health" || fail "final health endpoint"
echo

section "VALIDATION RESULT"
echo "Failures: $FAILURES"
echo "Warnings: $WARNINGS"
echo "Log: $LOG"

if [[ $FAILURES -ne 0 ]]; then
  echo "B3 BACKEND FULL VALIDATION: FAIL"
  exit 1
fi

if [[ $WARNINGS -ne 0 ]]; then
  echo "B3 BACKEND FULL VALIDATION: PASS WITH WARNINGS"
  exit 0
fi

echo "B3 BACKEND FULL VALIDATION: PASS"
