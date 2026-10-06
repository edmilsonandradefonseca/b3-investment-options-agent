"""Read-only active acceptance of covered CALL share reservations from the BTG snapshot."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from b3_agent.config import load_settings
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.providers.oplab.options import OplabOptionsAdapter
from b3_agent.repositories.market_data import MarketDataRepository
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
preferred = {"PETR4": 0, "ITUB4": 1, "BBDC4": 2, "VALE3": 3, "WEGE3": 4}
stocks.sort(key=lambda p: (preferred.get(p.ticker.upper(), 99), p.ticker.upper()))
adapter = OplabOptionsAdapter()
candidates = []

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
        candidates.append((ticker, contract, capacity, expected_rejection))
        break

assert candidates, "No executable CALL matched a real BTG holding with assessable coverage"
assert hashlib.sha256(portfolio_path.read_bytes()).hexdigest() == revision

# Report aggregate archive visibility only; do not expose portfolio symbols in
# the public Actions log.
market_archive = MarketDataRepository(settings.data_dir / "archive" / "cotahist_raw")
history_counts = [len(market_archive.read(position.ticker)) for position in stocks]
print(f"ACTIVE_LAB_CALL_DATA_ROOT_IS_SHARED={settings.data_dir == Path('/opt/b3-runtime/data')}", flush=True)
print(f"ACTIVE_LAB_CALL_STOCKS_WITH_LOCAL_HISTORY={sum(count > 0 for count in history_counts)}/{len(stocks)}", flush=True)
print(f"ACTIVE_LAB_CALL_LOCAL_HISTORY_ROWS={sum(history_counts)}", flush=True)

# Independently reconcile quantities from the same immutable snapshot before
# testing the live Strategy Lab implementation.
for ticker, contract, capacity, _ in candidates:
    manual_long = sum(float(p.quantity) for p in portfolio.positions
                      if p.instrument_type.upper() == "STOCK"
                      and p.ticker.upper() == ticker and p.quantity > 0)
    manual_committed = sum(abs(float(p.quantity)) * float(p.contract_multiplier)
                           for p in portfolio.positions
                           if p.instrument_type.upper() == "OPTION" and p.quantity < 0
                           and (p.option_type or "").upper() == "CALL"
                           and (p.underlying_ticker or "").strip().upper() == ticker)
    assert abs(capacity["long_shares"] - manual_long) < 1e-9
    assert abs(capacity["committed_shares"] - manual_committed) < 1e-9
    assert abs(capacity["available_shares"] - max(0.0, manual_long - manual_committed)) < 1e-9

candidate_history_counts = [len(market_archive.read(ticker)) for ticker, *_ in candidates]
print(f"ACTIVE_LAB_CALL_EXECUTABLE_CANDIDATES={len(candidates)}", flush=True)
print(f"ACTIVE_LAB_CALL_CANDIDATES_WITH_LOCAL_HISTORY={sum(count > 0 for count in candidate_history_counts)}/{len(candidates)}", flush=True)
print(f"ACTIVE_LAB_CALL_CANDIDATE_HISTORY_ROWS={sum(candidate_history_counts)}", flush=True)

service = LiveStrategyComparisonService()
data_blockers = set()
provider_failures = set()
accepted = False
for ticker, contract, capacity, expected_rejection in candidates:
    try:
        result = service.compare(
            assets=(ticker, ticker),
            strategies=("Manter", "Vender CALL coberta"),
            option_ids=(None, contract.option_id),
            amount=10_000.0,
            portfolio=portfolio,
            as_of=as_of,
        )
    except RuntimeError as exc:
        message = str(exc)
        if "market history unavailable for " in message:
            data_blockers.add("MARKET_HISTORY")
            detail = message.partition("market history unavailable for ")[2].partition(": ")[2]
            provider_failures.update(re.findall(r"\b(?:yahoo|oplab|brapi):([A-Za-z][A-Za-z0-9_]*)", detail))
            continue
        raise
    except ValueError as exc:
        message = str(exc)
        if expected_rejection and "is not covered" in message and "already committed to short CALLs" in message:
            assert hashlib.sha256(portfolio_path.read_bytes()).hexdigest() == revision
            print("ACTIVE_LAB_CALL_REJECTS_REUSED_COVERAGE=PASS", flush=True)
            accepted = True
            break
        if "current OPLAB price is required for covered CALL" in message:
            data_blockers.add("UNDERLYING_SPOT")
            continue
        raise
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
    accepted = True
    break

assert hashlib.sha256(portfolio_path.read_bytes()).hexdigest() == revision
print("ACTIVE_LAB_CALL_COVERAGE_RECONCILIATION=PASS", flush=True)
if not accepted:
    assert data_blockers, "No covered CALL candidate completed or returned an expected coverage rejection"
    reason = "_".join(sorted(data_blockers))
    print("ACTIVE_LAB_CALL_COMPARISON=BLOCKED_DATA", flush=True)
    print(f"ACTIVE_LAB_CALL_BLOCK_REASON={reason}", flush=True)
    if provider_failures:
        print("ACTIVE_LAB_CALL_PROVIDER_FAILURE_TYPES=" + ",".join(sorted(provider_failures)), flush=True)
    raise SystemExit(0)
print("ACTIVE_LAB_CALL_COVERAGE_FROM_CURRENT_BTG=PASS", flush=True)
