#!/usr/bin/env bash
set -u

repo=/opt/b3-investment-options-agent
ticker="${1:-PETR4}"
year="${2:-2026}"

cd "$repo" || exit 2

echo "===== V4.3 ASYNC ACCEPTANCE ====="
echo "ticker=$ticker year=$year"
echo

echo "===== STAGE 1 — ENQUEUE (NO DEEPSEEK INLINE) ====="
bash scripts/run_v43_async_acceptance.sh enqueue "$ticker" "$year"
enqueue_rc=$?
echo "ENQUEUE_RC=$enqueue_rc"
if [ "$enqueue_rc" -ne 0 ]; then
  echo "V4.3 acceptance stopped after enqueue failure."
  exit "$enqueue_rc"
fi

echo
echo "===== STAGE 2 — LOCAL WORKER ====="
bash scripts/run_v43_async_acceptance.sh worker "$ticker" "$year"
worker_rc=$?
echo "WORKER_RC=$worker_rc"
if [ "$worker_rc" -ne 0 ]; then
  echo "V4.3 acceptance stopped after worker failure."
  exit "$worker_rc"
fi

echo
echo "===== STAGE 3 — NONBLOCKING SENIOR CONTEXT ====="
bash scripts/run_v43_async_acceptance.sh context "$ticker" "$year"
context_rc=$?
echo "CONTEXT_RC=$context_rc"
if [ "$context_rc" -ne 0 ]; then
  echo "V4.3 acceptance stopped after context failure."
  exit "$context_rc"
fi

echo
echo "===== V4.3 ACCEPTANCE RESULT ====="
echo "ENQUEUE_RC=$enqueue_rc"
echo "WORKER_RC=$worker_rc"
echo "CONTEXT_RC=$context_rc"
echo "V4_3_ACCEPTANCE=PASS"
exit 0
