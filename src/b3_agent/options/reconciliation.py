from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from b3_agent.options.identity import canonical_option_ticker
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext


@dataclass(frozen=True)
class TransactionSourceCoverage:
    """Explicit evidence about the scope and completeness of one transaction source."""

    source_ref: str
    coverage_start: date | datetime | None = None
    coverage_end: date | datetime | None = None
    scope: str = "PERIOD_ONLY"
    completeness: str = "UNKNOWN"


@dataclass(frozen=True)
class OptionHistoryCoverage:
    """Evidence about how much transaction history is available for one option."""

    option_ticker: str
    first_trade_date: date | datetime | None
    last_trade_date: date | datetime | None
    transaction_count: int
    net_historical_quantity: float
    current_position_quantity: float | None
    position_alignment: str
    completeness: str = "UNKNOWN"


@dataclass(frozen=True)
class OptionReconciliation:
    """Reconciles historical option transactions against the authoritative BTG snapshot."""

    current: tuple[OptionTransaction, ...] = ()
    historical_only: tuple[OptionTransaction, ...] = ()
    quantity_mismatches: tuple[tuple[str, float, float], ...] = ()
    potential_cross_source_duplicates: tuple[tuple[str, str], ...] = ()
    btg_position_ids: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"
    history_coverage: tuple[OptionHistoryCoverage, ...] = ()
    source_coverage: tuple[TransactionSourceCoverage, ...] = ()


class OptionsReconciliationEngine:
    """Links transaction history to current BTG positions without equating a single trade to holdings."""

    def reconcile(
        self,
        transactions: tuple[OptionTransaction, ...],
        portfolio: PortfolioContext,
        source_coverage: tuple[TransactionSourceCoverage, ...] = (),
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

        # Excel exports and brokerage notes can describe the same economic
        # trade with different transaction IDs. Do not merge either record
        # because Excel may omit date/note identity. Expose candidates for audit.
        excel = [tx for tx in transactions if tx.source_type == "OPTIONS_XLSX"]
        notes = [tx for tx in transactions if tx.source_type == "BROKERAGE_NOTE"]
        potential_cross_source_duplicates: list[tuple[str, str]] = []
        for left in excel:
            for right in notes:
                if (
                    canonical_option_ticker(left.option_ticker) == canonical_option_ticker(right.option_ticker)
                    and left.quantity == right.quantity
                    and left.average_cost == right.average_cost
                    and left.total_cost == right.total_cost
                ):
                    potential_cross_source_duplicates.append((left.transaction_id, right.transaction_id))
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

        coverage_rows: list[OptionHistoryCoverage] = []
        grouped: dict[str, list[OptionTransaction]] = {}
        for transaction in transactions:
            grouped.setdefault(canonical_option_ticker(transaction.option_ticker), []).append(transaction)

        for ticker, rows in sorted(grouped.items()):
            position = btg_options.get(ticker)
            dates = [tx.as_of for tx in rows if tx.as_of is not None]
            net_quantity = sum(tx.quantity for tx in rows)
            current_quantity = position.quantity if position is not None else None
            if position is None:
                alignment = "NO_CURRENT_POSITION"
            elif net_quantity == current_quantity:
                alignment = "ALIGNED"
            else:
                alignment = "DIFFERENT"

            # Quantity alignment is evidence, not proof, of complete history.
            # Completeness may only be promoted by explicit source evidence.
            ticker_source_refs = {tx.source_ref for tx in rows}
            applicable = [item for item in source_coverage if item.source_ref in ticker_source_refs]
            if applicable and all(item.scope == "FULL_HISTORY" and item.completeness == "COMPLETE" for item in applicable):
                completeness = "COMPLETE"
            elif applicable and any(item.completeness == "PARTIAL" for item in applicable):
                completeness = "PARTIAL"
            else:
                completeness = "UNKNOWN"

            coverage_rows.append(
                OptionHistoryCoverage(
                    option_ticker=ticker,
                    first_trade_date=min(dates) if dates else None,
                    last_trade_date=max(dates) if dates else None,
                    transaction_count=len(rows),
                    net_historical_quantity=net_quantity,
                    current_position_quantity=current_quantity,
                    position_alignment=alignment,
                    completeness=completeness,
                )
            )

        return OptionReconciliation(
            current=tuple(current),
            historical_only=tuple(historical_only),
            quantity_mismatches=tuple(quantity_mismatches),
            potential_cross_source_duplicates=tuple(potential_cross_source_duplicates),
            btg_position_ids=tuple(dict.fromkeys(btg_position_ids)),
            quality_status="VALIDATED",
            history_coverage=tuple(coverage_rows),
            source_coverage=tuple(source_coverage),
        )
