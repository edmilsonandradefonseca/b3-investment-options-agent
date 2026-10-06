"""Read-only active Strategy Lab acceptance for stock vs PUT and explicit expiry shocks."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import subprocess

import httpx

from b3_agent.providers.oplab.options import OplabOptionsAdapter

runtime = Path("/opt/b3-investment-options-agent")
pid = int(subprocess.check_output([
    "systemctl", "show", "b3-runtime.service", "--property=MainPID", "--value"
], text=True, timeout=10))
assert pid > 0
boot = next(int(line.split()[1]) for line in Path("/proc/stat").read_text().splitlines()
            if line.startswith("btime "))
fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
started = boot + int(fields[19]) / os.sysconf("SC_CLK_TCK")
installed = runtime / "src/b3_agent/strategy_live.py"
checked_out = Path("src/b3_agent/strategy_live.py")
assert hashlib.sha256(installed.read_bytes()).digest() == hashlib.sha256(checked_out.read_bytes()).digest()
assert started >= installed.stat().st_mtime, "Restart required after installing Strategy Lab implementation"
print("ACTIVE_STRATEGY_LAB_REVISION=PASS", flush=True)

# Reuse the active service's OPLAB credential in memory; never print or persist it.
environ = Path(f"/proc/{pid}/environ").read_bytes().split(bytes((0,)))
token = next((entry.split(b"=", 1)[1].decode() for entry in environ
              if entry.startswith(b"OPLAB_API_TOKEN=")), None)
assert token, "Active runtime has no OPLAB credential; real option acceptance is unavailable"
os.environ["OPLAB_API_TOKEN"] = token
as_of = datetime.now(timezone.utc)
eligible = []
for ticker in ("PETR4", "ITUB4", "BBDC4", "VALE3", "WEGE3"):
    try:
        contracts, quotes = OplabOptionsAdapter().get_snapshot(ticker, as_of)
    except (OSError, RuntimeError, ValueError):
        continue
    quotes_by_id = {}
    for quote in quotes:
        quotes_by_id.setdefault(quote.option_id.upper(), []).append(quote)
    ticker_eligible = []
    for contract in contracts:
        quote_rows = quotes_by_id.get(contract.option_id.upper(), [])
        if (contract.option_type.upper() != "PUT" or contract.underlying_ticker.upper() != ticker
                or contract.expiration_date <= as_of.date() or len(quote_rows) != 1):
            continue
        quote = quote_rows[0]
        observed = quote.observation_timestamp
        available = quote.available_timestamp
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        if available.tzinfo is None:
            available = available.replace(tzinfo=timezone.utc)
        if (quote.bid is None or quote.bid <= 0 or observed > as_of or available > as_of
                or quote.quality_status in {"REJECTED", "INVALID"}
                or not quote.source or contract.contract_multiplier <= 0):
            continue
        ticker_eligible.append((contract, quote))
    if ticker_eligible:
        eligible = ticker_eligible
        underlying_ticker = ticker
        break
assert eligible, "No current executable PUT quote across tested underlyings; active action × PUT acceptance unavailable"
contract, chosen_quote = max(
    eligible,
    key=lambda row: ((row[1].open_interest or 0), (row[1].volume or 0),
                     -row[0].expiration_date.toordinal(), row[0].option_id),
)
horizon = contract.expiration_date.isoformat()
budget = float(contract.strike) * float(contract.contract_multiplier)
task = (f"Strategy Lab: compare comprar {underlying_ticker} com vender uma PUT exata "
        f"{contract.option_id}; horizonte {horizon}; testar choques hipotéticos "
        f"de -10%, 0% e +10% no vencimento. São cenários fornecidos, não previsões. "
        f"Use orçamento de R$ {budget:.2f}; não ordene nem recomende execução.")
request = {
    "task": task,
    "context": {
        "workspace": "Strategy Lab",
        "analysis_mode": "deterministic",
        "comparison_assets": [underlying_ticker, underlying_ticker],
        "strategy_a": "Comprar ação",
        "strategy_b": "Vender PUT",
        "option_a": None,
        "option_b": contract.option_id,
        "comparison_amount": budget,
        "scenario_horizon": horizon,
        "scenario_shocks_pct": [-10, 0, 10],
        "scenario_objective": "COMPARE_ONLY",
        "research_mode": "stored_only",
    },
}
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=120) as client:
    response = client.post("/orchestrate", json=request)
assert response.status_code == 200, f"Active Strategy Lab returned HTTP {response.status_code}"
envelope = response.json()
assert not envelope.get("error")
result = envelope["result"]
assert envelope["status"] == "COMPLETED"
assert result["telemetry"]["llm_calls"] == 0
alternatives = result["strategy_comparison"]["alternatives"]
assert {row["action_type"] for row in alternatives} == {"BUY_STOCK", "SELL_PUT"}
put_row = next(row for row in alternatives if row["action_type"] == "SELL_PUT")
assert put_row["subject_id"] == contract.option_id
assert put_row["capital_required"] == budget
assert put_row["assumptions"]["premium_basis"] == "current_bid"
assert result["option_evidence"][contract.option_id]["current_quote"]["bid"] > 0
scenario = result["scenario_analysis"]
assert scenario["horizon"] == horizon
assert scenario["user_supplied_shocks_pct"] == [-10, 0, 10]
assert scenario["probabilities"] is None
expected = {f"{horizon}:{shock:g}%" for shock in (-10, 0, 10)}
assert scenario["status"] == "COMPUTED"
assert all(set(row["pnl_by_scenario_brl"]) == expected for row in scenario["alternatives"])
assert scenario["ranking"] == "NOT_APPLIED"
print("ACTIVE_LAB_STOCK_VS_PUT=PASS", flush=True)
print("ACTIVE_LAB_EXPLICIT_EXPIRY_SCENARIOS=PASS", flush=True)
print("ACTIVE_LAB_NO_ORDER_SUBMITTED=PASS", flush=True)
