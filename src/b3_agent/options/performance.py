from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from b3_agent.options.identity import canonical_option_ticker
from b3_agent.options.lifecycle import OptionContract, OptionLifecycleEngine
from b3_agent.options.market_conventions import infer_b3_option_type
from b3_agent.schemas.option_transaction import OptionTransaction


@dataclass(frozen=True)
class OptionTradePerformance:
    """Performance of one reconstructed option lifecycle."""

    option_ticker: str
    underlying_ticker: str | None
    option_type: str | None
    first_trade_date: date | datetime | None
    last_trade_date: date | datetime | None
    status: str
    history_completeness: str
    transaction_count: int
    opened_quantity: float
    closed_quantity: float
    net_quantity: float
    premium_received: float
    premium_paid: float
    realized_pnl: float | None
    capital_basis: float | None
    return_pct: float | None
    return_basis: str
    days_in_trade: int | None
    expiration_date: date | None
    strike: float | None
    contract_multiplier: float | None


@dataclass(frozen=True)
class OptionUnderlyingPerformance:
    """Aggregated option performance for one underlying."""

    underlying_ticker: str
    realized_pnl: float
    put_pnl: float
    call_pnl: float
    premium_received: float
    premium_paid: float
    capital_basis: float
    return_pct: float | None
    lifecycle_count: int
    profitable_lifecycles: int
    losing_lifecycles: int


def _trade_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def _contract_for(
    ticker: str,
    contracts: dict[str, OptionContract],
) -> OptionContract | None:
    canonical = canonical_option_ticker(ticker)
    for key, contract in contracts.items():
        if canonical_option_ticker(key) == canonical:
            return contract
    return None


class OptionPerformanceEngine:
    """Build BI-ready option performance from deterministic lifecycle results.

    The engine deliberately distinguishes realized P&L from premium income and
    only calculates a return percentage when an explicit capital basis exists.
    For short puts the basis is strike notional (cash-secured capital proxy).
    Covered-call return requires the stock acquisition/market value at entry and
    therefore remains unavailable until that historical stock basis is modeled.
    """

    def __init__(self, lifecycle_engine: OptionLifecycleEngine | None = None) -> None:
        self.lifecycle_engine = lifecycle_engine or OptionLifecycleEngine()

    def build(
        self,
        transactions: Iterable[OptionTransaction],
        *,
        contracts: dict[str, OptionContract] | None = None,
        evaluation_date: date | datetime | None = None,
    ) -> tuple[OptionTradePerformance, ...]:
        rows = tuple(transactions)
        grouped: dict[str, list[OptionTransaction]] = {}
        for tx in rows:
            grouped.setdefault(canonical_option_ticker(tx.option_ticker), []).append(tx)

        contract_map = contracts or {}
        result: list[OptionTradePerformance] = []

        for ticker, trades in sorted(grouped.items()):
            contract = _contract_for(ticker, contract_map)
            lifecycle = self.lifecycle_engine.build(
                trades,
                contract=contract,
                evaluation_date=evaluation_date,
            )
            premium_received = round(
                sum(abs(tx.total_amount) for tx in trades if tx.side == "SELL" and tx.total_amount is not None),
                2,
            )
            premium_paid = round(
                sum(abs(tx.total_amount) for tx in trades if tx.side == "BUY" and tx.total_amount is not None),
                2,
            )

            multiplier = contract.contract_multiplier if contract and contract.contract_multiplier else 1.0
            capital_basis = None
            return_basis = "UNAVAILABLE"

            if contract and contract.strike is not None:
                short_qty = max(
                    (
                        sum(
                            tx.absolute_quantity
                            for tx in trades[: index + 1]
                            if tx.side == "SELL"
                        )
                        - sum(
                            tx.absolute_quantity
                            for tx in trades[: index + 1]
                            if tx.side == "BUY"
                        )
                        for index in range(len(trades))
                    ),
                    default=0.0,
                )
                if short_qty > 0:
                    capital_basis = round(
                        short_qty * contract.strike * multiplier, 2
                    )
                    if (option_type or "").upper() == "PUT":
                        return_basis = "CASH_SECURED_PUT_STRIKE_NOTIONAL"

            realized_pnl = lifecycle.realized_pnl
            return_pct = (
                round(realized_pnl / capital_basis * 100, 4)
                if realized_pnl is not None and capital_basis and return_basis != "UNAVAILABLE"
                else None
            )

            first = _trade_date(lifecycle.first_trade_date)
            last = _trade_date(lifecycle.last_trade_date)
            days = (last - first).days + 1 if first is not None and last is not None else None

            option_type = (contract.option_type if contract else None) or infer_b3_option_type(ticker)

            result.append(
                OptionTradePerformance(
                    option_ticker=lifecycle.option_ticker,
                    underlying_ticker=contract.underlying_ticker if contract else None,
                    option_type=option_type,
                    first_trade_date=lifecycle.first_trade_date,
                    last_trade_date=lifecycle.last_trade_date,
                    status=lifecycle.status,
                    history_completeness=lifecycle.history_completeness,
                    transaction_count=len(trades),
                    opened_quantity=lifecycle.opened_quantity,
                    closed_quantity=lifecycle.closed_quantity,
                    net_quantity=lifecycle.net_quantity,
                    premium_received=premium_received,
                    premium_paid=premium_paid,
                    realized_pnl=realized_pnl,
                    capital_basis=capital_basis,
                    return_pct=return_pct,
                    return_basis=return_basis,
                    days_in_trade=days,
                    expiration_date=contract.expiration_date if contract else None,
                    strike=contract.strike if contract else None,
                    contract_multiplier=contract.contract_multiplier if contract else None,
                )
            )

        return tuple(result)

    def aggregate_by_underlying(
        self,
        performances: Iterable[OptionTradePerformance],
    ) -> tuple[OptionUnderlyingPerformance, ...]:
        grouped: dict[str, list[OptionTradePerformance]] = {}
        for item in performances:
            underlying = item.underlying_ticker or "UNKNOWN"
            grouped.setdefault(underlying, []).append(item)

        result: list[OptionUnderlyingPerformance] = []
        for underlying, rows in sorted(grouped.items()):
            realized_values = [x.realized_pnl for x in rows if x.realized_pnl is not None]
            realized_pnl = round(sum(realized_values), 2)
            put_pnl = round(
                sum(x.realized_pnl or 0.0 for x in rows if (x.option_type or "").upper() == "PUT"),
                2,
            )
            call_pnl = round(
                sum(x.realized_pnl or 0.0 for x in rows if (x.option_type or "").upper() == "CALL"),
                2,
            )
            capital = round(sum(x.capital_basis or 0.0 for x in rows), 2)
            return_pct = (
                round(realized_pnl / capital * 100, 4)
                if capital > 0 and realized_values
                else None
            )
            result.append(
                OptionUnderlyingPerformance(
                    underlying_ticker=underlying,
                    realized_pnl=realized_pnl,
                    put_pnl=put_pnl,
                    call_pnl=call_pnl,
                    premium_received=round(sum(x.premium_received for x in rows), 2),
                    premium_paid=round(sum(x.premium_paid for x in rows), 2),
                    capital_basis=capital,
                    return_pct=return_pct,
                    lifecycle_count=len(rows),
                    profitable_lifecycles=sum(
                        x.realized_pnl is not None and x.realized_pnl > 0 for x in rows
                    ),
                    losing_lifecycles=sum(
                        x.realized_pnl is not None and x.realized_pnl < 0 for x in rows
                    ),
                )
            )

        return tuple(result)
