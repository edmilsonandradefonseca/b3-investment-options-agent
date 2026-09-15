from __future__ import annotations

from dataclasses import dataclass

from b3_agent.options.identity import canonical_option_ticker
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext


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
            canonical_option_ticker(position.ticker): position
            for position in portfolio.positions
            if position.instrument_type == "OPTION"
        }

        current: list[OptionTransaction] = []
        historical_only: list[OptionTransaction] = []
        mismatches: list[tuple[str, float, float]] = []
        btg_position_ids: list[str] = []

        for transaction in transactions:
            canonical_ticker = canonical_option_ticker(transaction.option_ticker)
            position = btg_options.get(canonical_ticker)
            if position is None:
                historical_only.append(transaction)
                continue

            current.append(transaction)
            btg_position_ids.append(position.position_id)

            if transaction.quantity != position.quantity:
                mismatches.append(
                    (canonical_ticker, transaction.quantity, position.quantity)
                )

        quality_status = "WARNING" if mismatches else "VALIDATED"
        return OptionReconciliation(
            current=tuple(current),
            historical_only=tuple(historical_only),
            quantity_mismatches=tuple(mismatches),
            btg_position_ids=tuple(btg_position_ids),
            quality_status=quality_status,
        )
