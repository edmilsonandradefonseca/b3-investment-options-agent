from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from b3_agent.options.identity import canonical_option_ticker
from b3_agent.options.lifecycle import OptionContract
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.options.performance import OptionPerformanceEngine
from b3_agent.repositories.option_contract_registry import OptionContractRegistry
from b3_agent.repositories.option_ledger import OptionTransactionLedger

ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = Path(os.getenv("B3_AGENT_OPTION_LEDGER_PATH", str(ROOT / "data" / "option_transactions.sqlite3"))).expanduser().resolve()
REGISTRY_PATH = Path(os.getenv("B3_AGENT_OPTION_CONTRACT_REGISTRY_PATH", str(ROOT / "data" / "option_contracts.sqlite3"))).expanduser().resolve()

app = FastAPI(title="B3 Investment Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _contract_map() -> dict[str, OptionContract]:
    records = OptionContractRegistry(REGISTRY_PATH).list_all()
    return {
        record.option_ticker: OptionContract(
            option_ticker=record.option_ticker,
            expiration_date=record.expiration_date,
            option_type=record.option_type,
            strike=record.strike,
            underlying_ticker=record.underlying_ticker,
            contract_multiplier=record.contract_multiplier,
        )
        for record in records
    }


def _row(item) -> dict[str, Any]:
    return {
        "option_ticker": item.option_ticker,
        "underlying_ticker": item.underlying_ticker,
        "option_type": item.option_type,
        "first_trade_date": _iso(item.first_trade_date),
        "last_trade_date": _iso(item.last_trade_date),
        "status": item.status,
        "history_completeness": item.history_completeness,
        "transaction_count": item.transaction_count,
        "opened_quantity": item.opened_quantity,
        "closed_quantity": item.closed_quantity,
        "net_quantity": item.net_quantity,
        "premium_received": item.premium_received,
        "premium_paid": item.premium_paid,
        "realized_pnl": item.realized_pnl,
        "capital_basis": item.capital_basis,
        "return_pct": item.return_pct,
        "return_basis": item.return_basis,
        "days_in_trade": item.days_in_trade,
        "expiration_date": _iso(item.expiration_date),
        "strike": item.strike,
        "contract_multiplier": item.contract_multiplier,
    }


def _portfolio_snapshot_path() -> Path | None:
    # Keep the API on the same authoritative configuration used by Streamlit.
    configured = os.getenv("B3_AGENT_PORTFOLIO_FILE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    # Backward-compatible explicit API override; no guessed local file is used.
    override = os.getenv("B3_AGENT_PORTFOLIO_PATH", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    return None


def _portfolio_row(position) -> dict[str, Any]:
    cost_basis = None
    pnl = None
    pnl_pct = None
    if position.average_cost is not None:
        cost_basis = position.quantity * position.average_cost
        if position.market_value is not None:
            pnl = position.market_value - cost_basis
            if cost_basis:
                pnl_pct = pnl / abs(cost_basis) * 100
    return {
        "ticker": position.ticker,
        "instrument_type": position.instrument_type,
        "quantity": position.quantity,
        "average_cost": position.average_cost,
        "market_price": position.market_price,
        "market_value": position.market_value,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "option_type": position.option_type,
        "underlying_ticker": position.underlying_ticker,
        "strike": position.strike,
        "expiration_date": _iso(position.expiration_date),
    }


@app.get("/api/portfolio")
def portfolio_snapshot() -> dict[str, Any]:
    path = _portfolio_snapshot_path()
    if path is None:
        return {
            "status": "NO_SNAPSHOT",
            "message": "No BTG portfolio configured. Set B3_AGENT_PORTFOLIO_FILE to the same XLSX used by the Streamlit dashboard.",
            "positions": [],
        }
    if not path.exists():
        return {
            "status": "NO_SNAPSHOT",
            "message": f"Portfolio file not found: {path}",
            "positions": [],
        }

    try:
        portfolio = BtgRendaVariavelLoader().load(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Portfolio snapshot inválido: {exc}") from exc

    rows = [_portfolio_row(position) for position in portfolio.positions]
    stock_value = sum(
        row["market_value"] or 0
        for row in rows
        if row["instrument_type"] == "STOCK"
    )
    option_value = sum(
        row["market_value"] or 0
        for row in rows
        if row["instrument_type"] == "OPTION"
    )
    total_value = stock_value + option_value + portfolio.cash

    return {
        "status": "OK",
        "as_of": _iso(portfolio.as_of),
        "quality_status": portfolio.quality_status,
        "cash": portfolio.cash,
        "summary": {
            "total_value": total_value,
            "stock_value": stock_value,
            "option_value": option_value,
            "position_count": len(rows),
        },
        "positions": rows,
        "source": str(path),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/options/analytics")
def options_analytics(
    underlying: str = Query("Todos"),
    option_type: str = Query("Todas"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
) -> dict[str, Any]:
    transactions = OptionTransactionLedger(LEDGER_PATH).list_all()
    if not transactions:
        return {
            "filters": {"underlying": underlying, "option_type": option_type},
            "summary": {"realized_pnl": 0.0, "premium_received": 0.0, "premium_paid": 0.0, "return_pct": None},
            "lifecycles": [],
            "transactions": [],
            "data_quality": {"status": "NO_TRANSACTIONS"},
        }

    contracts = _contract_map()

    def contract_for(ticker: str) -> OptionContract | None:
        canonical = canonical_option_ticker(ticker)
        for key, value in contracts.items():
            if canonical_option_ticker(key) == canonical:
                return value
        return None

    filtered = []
    for tx in transactions:
        if start_date and tx.as_of and tx.as_of.date() if hasattr(tx.as_of, "date") else start_date and tx.as_of:
            pass
        tx_date = tx.as_of.date() if hasattr(tx.as_of, "date") else tx.as_of
        if start_date and (tx_date is None or tx_date < start_date):
            continue
        if end_date and (tx_date is None or tx_date > end_date):
            continue
        contract = contract_for(tx.option_ticker)
        known_underlying = contract.underlying_ticker if contract else None
        if underlying.upper() != "TODOS" and (known_underlying or "").upper() != underlying.upper():
            continue
        if option_type.upper() != "TODAS":
            inferred = (contract.option_type if contract else None)
            if not inferred:
                from b3_agent.options.market_conventions import infer_b3_option_type
                inferred = infer_b3_option_type(tx.option_ticker)
            if (inferred or "").upper() != option_type.upper():
                continue
        filtered.append(tx)

    if not filtered:
        return {
            "filters": {"underlying": underlying, "option_type": option_type},
            "summary": {"realized_pnl": 0.0, "premium_received": 0.0, "premium_paid": 0.0, "return_pct": None},
            "lifecycles": [],
            "transactions": [],
            "data_quality": {
                "status": "NO_MATCH",
                "note": "Underlying filtering depends on contract metadata in the registry. Historical transactions without metadata are not silently assigned to an underlying.",
            },
        }

    performances = OptionPerformanceEngine().build(filtered, contracts=contracts, evaluation_date=end_date)
    rows = [_row(item) for item in performances]

    realized = [x["realized_pnl"] for x in rows if x["realized_pnl"] is not None]
    premium_received = sum(x["premium_received"] for x in rows)
    premium_paid = sum(x["premium_paid"] for x in rows)
    capital = sum(x["capital_basis"] or 0 for x in rows)
    return_pct = round(sum(realized) / capital * 100, 4) if realized and capital else None

    transaction_rows = [
        {
            "transaction_id": tx.transaction_id,
            "option_ticker": tx.option_ticker,
            "date": _iso(tx.as_of),
            "side": tx.side,
            "quantity": tx.quantity,
            "execution_price": tx.execution_price,
            "total_amount": tx.total_amount,
            "source_type": tx.source_type,
            "source_id": tx.source_id,
            "note_number": tx.note_number,
        }
        for tx in filtered
    ]

    return {
        "filters": {"underlying": underlying, "option_type": option_type, "start_date": _iso(start_date), "end_date": _iso(end_date)},
        "summary": {
            "realized_pnl": round(sum(realized), 2),
            "premium_received": round(premium_received, 2),
            "premium_paid": round(premium_paid, 2),
            "capital_basis": round(capital, 2),
            "return_pct": return_pct,
            "lifecycle_count": len(rows),
            "profitable_lifecycles": sum(x["realized_pnl"] is not None and x["realized_pnl"] > 0 for x in rows),
            "losing_lifecycles": sum(x["realized_pnl"] is not None and x["realized_pnl"] < 0 for x in rows),
        },
        "lifecycles": rows,
        "transactions": transaction_rows,
        "data_quality": {
            "status": "OK",
            "transactions_included": len(filtered),
            "warning": "Realized P&L is option-leg gross P&L. Covered-call economics require the stock basis to be modeled separately.",
        },
    }
