from __future__ import annotations

from dataclasses import dataclass

from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext, Position


@dataclass(frozen=True)
class OptionReconciliation:
    """Reconciles historical transactions against the authoritative BTG snapshot."""

    current: tuple[OptionTransaction, ...] = ()
    historical_only: tuple[OptionTransaction, ...] = ()
    quantity_mismatches: tuple[tuple[str, float, float], ...] = ()
    btg_position_ids: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"


class OptionsReconciliationEngine:
    """BTG wins for current state; transactions remain historical provenance."""

    def reconcile(
        self,
        transactions: tuple[OptionTransaction, ...],
        portfolio: PortfolioContext,
    ) -> OptionReconciliation:
        btg_options = {
            position.ticker: position
            for position in portfolio.positions
            if position.instrument_type == "OPTION"
        }

        current: list[OptionTransaction] = []
        historical_only: list[OptionTransaction] = []
        mismatches: list[tuple[str, float, float]] = []

        for transaction in transactions:
            position = btg_options.get(transaction.option_ticker)
            if position is None:
                historical_only.append(transaction)
                continue
            current.append(transaction)
            if transaction.quantity != position.quantity:
                mismatches.append(
                    (transaction.option_ticker, transaction.quantity, position.quantity)
                )

        quality_status = "WARNING" if mismatches else "VALIDATED"
        return OptionReconciliation(
            current=tuple(current),
            historical_only=tuple(historical_only),
            quantity_mismatches=tuple(mismatches),
            btg_position_ids=tuple(sorted(btg_options)),
            quality_status=quality_status,
        )
