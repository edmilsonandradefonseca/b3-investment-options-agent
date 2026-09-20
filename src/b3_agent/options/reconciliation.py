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
class ReconciliationMatch:
    """Auditable relationship between transactions from different sources."""

    status: str
    excel_transaction_id: str | None = None
    brokerage_transaction_id: str | None = None
    reason: str = ""


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
    matches: tuple[ReconciliationMatch, ...] = ()


class OptionsReconciliationEngine:
    """Links transaction history to current BTG positions without equating a trade to holdings."""

    @staticmethod
    def _same_economic_trade(left: OptionTransaction, right: OptionTransaction) -> bool:
        """Match fields that both the XLSX and brokerage-note sources expose."""
        return (
            canonical_option_ticker(left.option_ticker)
            == canonical_option_ticker(right.option_ticker)
            and left.quantity == right.quantity
            and left.average_cost == right.average_cost
            and left.total_cost == right.total_cost
        )

    @staticmethod
    def _same_candidate(left: OptionTransaction, right: OptionTransaction) -> bool:
        """Identify a possible duplicate when the economic values are not identical."""
        return (
            canonical_option_ticker(left.option_ticker)
            == canonical_option_ticker(right.option_ticker)
            and left.quantity == right.quantity
        )

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
        # exists in the authoritative BTG snapshot. Individual transaction
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

        excel = [tx for tx in transactions if tx.source_type == "OPTIONS_XLSX"]
        notes = [tx for tx in transactions if tx.source_type == "BROKERAGE_NOTE"]

        matches: list[ReconciliationMatch] = []
        potential_cross_source_duplicates: list[tuple[str, str]] = []
        paired_excel: set[str] = set()
        paired_notes: set[str] = set()

        # Pair each exact economic match once. Transaction IDs are source-local,
        # so they are evidence of provenance, not the reconciliation key.
        for left in excel:
            for right in notes:
                if right.transaction_id in paired_notes:
                    continue
                if self._same_economic_trade(left, right):
                    paired_excel.add(left.transaction_id)
                    paired_notes.add(right.transaction_id)
                    matches.append(
                        ReconciliationMatch(
                            status="RECONCILED",
                            excel_transaction_id=left.transaction_id,
                            brokerage_transaction_id=right.transaction_id,
                            reason="same ticker, signed quantity, execution price and total amount",
                        )
                    )
                    break

        # Same ticker + signed quantity without an exact economic match is an
        # auditable candidate, not an automatic merge.
        for left in excel:
            for right in notes:
                if (
                    left.transaction_id not in paired_excel
                    and right.transaction_id not in paired_notes
                    and self._same_candidate(left, right)
                ):
                    potential_cross_source_duplicates.append(
                        (left.transaction_id, right.transaction_id)
                    )
                    matches.append(
                        ReconciliationMatch(
                            status="POTENTIAL_DUPLICATE",
                            excel_transaction_id=left.transaction_id,
                            brokerage_transaction_id=right.transaction_id,
                            reason="same ticker and signed quantity but different economic fields",
                        )
                    )

        for transaction in excel:
            if transaction.transaction_id not in paired_excel:
                matches.append(
                    ReconciliationMatch(
                        status="EXCEL_ONLY",
                        excel_transaction_id=transaction.transaction_id,
                        reason="no exact brokerage-note match",
                    )
                )

        for transaction in notes:
            if transaction.transaction_id not in paired_notes:
                matches.append(
                    ReconciliationMatch(
                        status="BROKERAGE_ONLY",
                        brokerage_transaction_id=transaction.transaction_id,
                        reason="no exact Excel transaction match",
                    )
                )

        quantity_mismatches: list[tuple[str, float, float]] = []

        coverage_by_ref = {item.source_ref: item for item in source_coverage}
        grouped: dict[str, list[OptionTransaction]] = {}
        for transaction in transactions:
            grouped.setdefault(
                canonical_option_ticker(transaction.option_ticker), []
            ).append(transaction)

        coverage_rows: list[OptionHistoryCoverage] = []
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

            applicable = [
                coverage_by_ref[tx.source_ref]
                for tx in rows
                if tx.source_ref in coverage_by_ref
            ]
            if applicable and all(
                item.scope == "FULL_HISTORY" and item.completeness == "COMPLETE"
                for item in applicable
            ):
                completeness = "COMPLETE"
            elif applicable and any(
                item.completeness == "PARTIAL" for item in applicable
            ):
                completeness = "PARTIAL"
            else:
                completeness = "UNKNOWN"

            if (
                position is not None
                and completeness == "COMPLETE"
                and net_quantity != position.quantity
            ):
                quantity_mismatches.append(
                    (ticker, net_quantity, position.quantity)
                )

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

        quality_status = (
            "WARNING"
            if quantity_mismatches or potential_cross_source_duplicates
            else "VALIDATED"
        )

        return OptionReconciliation(
            current=tuple(current),
            historical_only=tuple(historical_only),
            quantity_mismatches=tuple(quantity_mismatches),
            potential_cross_source_duplicates=tuple(
                potential_cross_source_duplicates
            ),
            btg_position_ids=tuple(dict.fromkeys(btg_position_ids)),
            quality_status=quality_status,
            history_coverage=tuple(coverage_rows),
            source_coverage=tuple(source_coverage),
            matches=tuple(matches),
        )
