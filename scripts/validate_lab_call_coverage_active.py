"""Read-only active acceptance of covered CALL share reservations from the BTG snapshot."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from b3_agent.config import load_settings
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.providers.oplab.options import OplabOptionsAdapter
from b3_agent.strategy_live import LiveStrategyComparisonService, _covered_call_capacity

runtime = Path("/opt/b3-investment-options-agent")
pid = int(subprocess.check_output([
    "systemctl", "show", "b3-runtime.service", "--property=MainPID", "--value"
], text=True, timeout=10))
assert pid > 0
boot = next(int(line.split()[1]) for line in Path("/proc/stat").read_text().splitlines()
            if line.startswith("btime "))
fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
started = boot + int(fields[19]) / os.sysconf("SC_CLK_TCK")
source = Path("src/b3_agent/strategy_live.py")
installed = runtime / source
assert hashlib.sha256(installed.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
assert started >= installed.stat().st_mtime, "Restart required after installing Strategy Lab implementation"

for field in Path(f"/proc/{pid}/environ").read_bytes().split(bytes((0,))):
    key, sep, value = field.partition(b"=")
    name = key.decode()
    if sep and (name.startswith("B3_") or name in {"OPLAB_API_TOKEN", "BRAPI_TOKEN"}):
        os.environ[name] = value.decode()

settings = load_settings()
portfolio_path = settings.data_dir / "imports" / "portfolio.xlsx"
revision = hashlib.sha256(portfolio_path.read_bytes()).hexdigest()
portfolio = BtgRendaVariavelLoader().load(portfolio_path)
as_of = datetime.now(timezone.utc)
stocks = [p for p in portfolio.positions
          if p.instrument_type.upper() == "STOCK" and p.quantity > 0]
adapter = OplabOptionsAdapter()
candidate = None
expected_rejection = False

for stock in stocks:
    ticker = stock.ticker.upper()
    capacity = _covered_call_capacity(ticker, portfolio)
    if capacity["long_shares"] <= 0:
        continue
    try:
        contracts, quotes = adapter.get_snapshot(ticker, as_of)
    except (OSError, RuntimeError, ValueError):
        continue
    quote_by_id = {}
    for quote in quotes:
        quote_by_id.setdefault(quote.option_id.upper(), quote)
    for contract in contracts:
        quote = quote_by_id.get(contract.option_id.upper())
        if (contract.option_type.upper() != "CALL"
                or contract.underlying_ticker.upper() != ticker
                or contract.expiration_date <= as_of.date()
                or quote is None or quote.bid is None or quote.bid <= 0
                or contract.contract_multiplier <= 0
                or contract.contract_multiplier > capacity["long_shares"]):
            continue
        if capacity["available_shares"] >= contract.contract_multiplier:
            expected_rejection = False
        elif (capacity["committed_shares"] > 0
              and capacity["available_shares"] < contract.contract_multiplier):
            expected_rejection = True
        else:
            continue
        candidate = (ticker, contract, capacity)
        break
    if candidate:
        break

assert candidate, "No executable CALL matched a real BTG holding with assessable coverage"
ticker, contract, capacity = candidate
assert hashlib.sha256(portfolio_path.read_bytes()).hexdigest() == revision

service = LiveStrategyComparisonService()
try:
    result = service.compare(
        assets=(ticker, ticker),
        strategies=("Manter", "Vender CALL coberta"),
        option_ids=(None, contract.option_id),
        amount=10_000.0,
        portfolio=portfolio,
        as_of=as_of,
    )
except ValueError as exc:
    if not expected_rejection:
        raise
    message = str(exc)
    assert "is not covered" in message and "already committed to short CALLs" in message
    assert hashlib.sha256(portfolio_path.read_bytes()).hexdigest() == revision
    print("ACTIVE_LAB_CALL_REJECTS_REUSED_COVERAGE=PASS", flush=True)
else:
    assert not expected_rejection, "Active service reused shares already committed to an open short CALL"
    alternatives = result["strategy_comparison"]["alternatives"]
    call = next(row for row in alternatives if row["action_type"] == "SELL_CALL")
    assumptions = call["assumptions"]
    assert assumptions["covered_call"] is True
    assert assumptions["covered_shares_free_before_trade"] >= assumptions["covered_shares_required"]
    assert assumptions["stock_shares_available"] == capacity["long_shares"]
    assert assumptions["covered_shares_already_committed"] == capacity["committed_shares"]
    assert assumptions["existing_short_call_position_ids"] == capacity["committed_call_position_ids"]
    assert result["option_evidence"][contract.option_id]["current_quote"]["bid"] > 0
    assert hashlib.sha256(portfolio_path.read_bytes()).hexdigest() == revision
    print("ACTIVE_LAB_CALL_FREE_COVERAGE=PASS", flush=True)

print("ACTIVE_LAB_CALL_COVERAGE_FROM_CURRENT_BTG=PASS", flush=True)
