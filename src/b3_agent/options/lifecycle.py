from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from b3_agent.schemas.option_transaction import OptionTransaction


@dataclass(frozen=True)
class OptionContract:
    """Contract metadata required to classify an option at expiration."""

    option_ticker: str
    expiration_date: date | None = None
    option_type: str | None = None
    strike: float | None = None
    underlying_ticker: str | None = None
    contract_multiplier: float | None = None


@dataclass(frozen=True)
class OptionLifecycle:
    """Deterministic lifecycle and realized gross P&L derived from history."""

    option_ticker: str
    status: str
    net_quantity: float
    opened_quantity: float
    closed_quantity: float
    unmatched_quantity: float
    realized_pnl: float | None
    first_trade_date: date | datetime | None
    last_trade_date: date | datetime | None
    expiration_date: date | None = None
    expiry_state: str = "NOT_PROVIDED"
    history_completeness: str = "UNKNOWN"
    contract_metadata_quality: str = "MISSING"
    pnl_basis: str = "GROSS_UNIT_PRICE"


@dataclass
class _Lot:
    side: str
    quantity: float
    price: float | None


def _trade_date(transaction: OptionTransaction) -> date | datetime:
    return transaction.as_of if transaction.as_of is not None else date.min


def _pair_pnl(
    open_lot: _Lot,
    close_side: str,
    quantity: float,
    close_price: float | None,
) -> float | None:
    if open_lot.price is None or close_price is None:
        return None
    if open_lot.side == "BUY" and close_side == "SELL":
        return (close_price - open_lot.price) * quantity
    if open_lot.side == "SELL" and close_side == "BUY":
        return (open_lot.price - close_price) * quantity
    raise ValueError("opening and closing sides must be opposite")


class OptionLifecycleEngine:
    """Reconstruct option lifecycle using FIFO matching of opposite-side trades."""

    def build(
        self,
        transactions: Iterable[OptionTransaction],
        *,
        contract: OptionContract | None = None,
        evaluation_date: date | datetime | None = None,
        expiry_outcome: str | None = None,
    ) -> OptionLifecycle:
        ordered = tuple(sorted(transactions, key=lambda tx: (_trade_date(tx), tx.transaction_id)))
        if not ordered:
            raise ValueError("at least one transaction is required")

        ticker = ordered[0].option_ticker
        if any(tx.option_ticker != ticker for tx in ordered):
            raise ValueError("all transactions must belong to the same option ticker")

        lots: deque[_Lot] = deque()
        realized_pnl = 0.0
        realized_has_unpriced = False
        opened_quantity = 0.0
        closed_quantity = 0.0

        for tx in ordered:
            remaining = tx.absolute_quantity
            side = tx.side

            while remaining > 0 and lots and lots[0].side != side:
                lot = lots[0]
                matched = min(remaining, lot.quantity)
                pnl = _pair_pnl(lot, side, matched, tx.execution_price)
                if pnl is None:
                    realized_has_unpriced = True
                else:
                    realized_pnl += pnl
                lot.quantity -= matched
                remaining -= matched
                closed_quantity += matched
                if lot.quantity <= 0:
                    lots.popleft()

            if remaining > 0:
                lots.append(_Lot(side=side, quantity=remaining, price=tx.execution_price))
                opened_quantity += remaining

        net_quantity = sum(
            lot.quantity if lot.side == "BUY" else -lot.quantity for lot in lots
        )
        unmatched_quantity = sum(lot.quantity for lot in lots)

        if expiry_outcome:
            normalized_outcome = expiry_outcome.strip().upper()
            if normalized_outcome not in {"WORTHLESS", "EXERCISED", "ASSIGNED"}:
                raise ValueError("expiry_outcome must be WORTHLESS, EXERCISED or ASSIGNED")

            # A worthless expiry closes the remaining economic position without
            # an opposite trade. For gross unit-price P&L, the option premium
            # is realized at expiry: a short position keeps the premium
            # received, while a long position loses the premium paid.
            if normalized_outcome == "WORTHLESS":
                for lot in lots:
                    if lot.price is None:
                        realized_has_unpriced = True
                        continue
                    if lot.side == "SELL":
                        realized_pnl += lot.price * lot.quantity
                    else:
                        realized_pnl -= lot.price * lot.quantity

            status = {
                "WORTHLESS": "EXPIRED_WORTHLESS",
                "EXERCISED": "EXERCISED",
                "ASSIGNED": "ASSIGNED",
            }[normalized_outcome]
            expiry_state = normalized_outcome
        elif contract is not None and contract.expiration_date is not None:
            check_date = evaluation_date or _trade_date(ordered[-1])
            if check_date >= contract.expiration_date and abs(net_quantity) > 0:
                status = "EXPIRED_UNRESOLVED"
                expiry_state = "EXPIRED_UNRESOLVED"
            elif abs(net_quantity) == 0:
                status = "CLOSED"
                expiry_state = "ACTIVE"
            else:
                status = "OPEN"
                expiry_state = "ACTIVE"
        elif abs(net_quantity) == 0:
            status = "CLOSED"
            expiry_state = "NOT_PROVIDED"
        else:
            status = "OPEN"
            expiry_state = "NOT_PROVIDED"

        history_completeness = (
            "COMPLETE" if abs(net_quantity) == 0 else "PARTIAL_OR_OPEN"
        )

        metadata_values = (
            contract.expiration_date if contract else None,
            contract.option_type if contract else None,
            contract.strike if contract else None,
            contract.underlying_ticker if contract else None,
        )
        contract_metadata_quality = (
            "COMPLETE"
            if all(value is not None for value in metadata_values)
            else "PARTIAL"
            if any(value is not None for value in metadata_values)
            else "MISSING"
        )

        return OptionLifecycle(
            option_ticker=ticker,
            status=status,
            net_quantity=net_quantity,
            opened_quantity=opened_quantity,
            closed_quantity=closed_quantity,
            unmatched_quantity=unmatched_quantity,
            realized_pnl=None if realized_has_unpriced else round(realized_pnl, 2),
            first_trade_date=ordered[0].as_of,
            last_trade_date=ordered[-1].as_of,
            expiration_date=contract.expiration_date if contract else None,
            expiry_state=expiry_state,
            history_completeness=history_completeness,
            contract_metadata_quality=contract_metadata_quality,
        )


def build_option_lifecycles(
    transactions: Iterable[OptionTransaction],
    *,
    contracts: dict[str, OptionContract] | None = None,
    evaluation_date: date | datetime | None = None,
) -> tuple[OptionLifecycle, ...]:
    """Build one lifecycle per option ticker."""

    grouped: dict[str, list[OptionTransaction]] = {}
    for transaction in transactions:
        grouped.setdefault(transaction.option_ticker, []).append(transaction)

    engine = OptionLifecycleEngine()
    return tuple(
        engine.build(
            rows,
            contract=(contracts or {}).get(ticker),
            evaluation_date=evaluation_date,
        )
        for ticker, rows in sorted(grouped.items())
    )
