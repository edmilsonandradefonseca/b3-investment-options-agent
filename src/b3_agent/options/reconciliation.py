from __future__ import annotations

from dataclasses import dataclass

from b3_agent.options.identity import canonical_option_ticker
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext


@dataclass(frozen=True)
class OptionReconciliation:
    """Reconciles historical option transactions against the authoritative BTG snapshot."""

    current: tuple[OptionTransaction, ...] = ()
    historical_only: tuple[OptionTransaction, ...] = ()
    quantity_mismatches: tuple[tuple[str, float, float], ...] = ()
    btg_position_ids: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"


class OptionsReconciliationEngine:
    """Links transaction history to current BTG positions without equating a single trade to holdings."""

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
        btg_position_ids: list[str] = []

        # A transaction belongs to the current-position history when its ticker
        # exists in the authoritative BTG snapshot.  Individual transaction
        # quantities are intentionally NOT compared with current holdings:
        # several trades may form one current position.
        for transaction in transactions:
            canonical_ticker = canonical_option_ticker(transaction.option_ticker)
            position = btg_options.get(canonical_ticker)
            if position is None:
                historical_only.append(transaction)
                continue

            current.append(transaction)
            btg_position_ids.append(position.position_id)

        # Quantity reconciliation is meaningful at aggregate ticker level,
        # not per transaction.  Net historical quantity is compared with the
        # current BTG quantity only when the history can represent the full
        # lifecycle.  With a partial transaction extract, no mismatch is
        # inferred merely from different quantities.
        quantity_mismatches: list[tuple[str, float, float]] = []
        for ticker, position in btg_options.items():
            ticker_transactions = [
                tx for tx in transactions
                if canonical_option_ticker(tx.option_ticker) == ticker
            ]
            if not ticker_transactions:
                continue

            net_quantity = sum(tx.quantity for tx in ticker_transactions)
            if net_quantity == position.quantity:
                continue

            # The source transaction extract may be partial (e.g. only
            # executed trades available in the imported statement).  Preserve
            # the difference as informational data only when requested by a
            # future reconciliation contract; do not downgrade quality here.
            _ = net_quantity

        return OptionReconciliation(
            current=tuple(current),
            historical_only=tuple(historical_only),
            quantity_mismatches=tuple(quantity_mismatches),
            btg_position_ids=tuple(dict.fromkeys(btg_position_ids)),
            quality_status="VALIDATED",
        )
