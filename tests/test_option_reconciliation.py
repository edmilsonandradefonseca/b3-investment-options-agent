from datetime import date

from b3_agent.options.reconciliation import (
    OptionsReconciliationEngine,
    ReconciliationMatch,
    TransactionSourceCoverage,
)
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext, Position


def _portfolio(*tickers: str) -> PortfolioContext:
    return PortfolioContext(
        as_of=date(2026, 9, 11),
        positions=tuple(
            Position(
                position_id=f"btg:{ticker}",
                ticker=ticker,
                instrument_type="OPTION",
                quantity=-7000,
                strike=15.30,
                expiration_date=date(2026, 10, 16),
                option_type="PUT",
                underlying_ticker="ABEV3",
                market_price=0.28,
                market_value=-1960,
            )
            for ticker in tickers
        ),
        source_refs=("BTG:Renda Variavel",),
        quality_status="VALIDATED",
    )


def test_reconciliation_classifies_current_and_historical_transactions() -> None:
    transactions = (
        OptionTransaction("t1", "ABEVV153", "BTG", -7000, 0.48, -3349.04),
        OptionTransaction("t2", "TOTSI385", "BTG", 3000, 0.30, 902.09),
    )

    result = OptionsReconciliationEngine().reconcile(transactions, _portfolio("ABEVV153"))

    assert [item.option_ticker for item in result.current] == ["ABEVV153"]
    assert [item.option_ticker for item in result.historical_only] == ["TOTSI385"]
    assert result.quantity_mismatches == ()
    assert result.quality_status == "VALIDATED"


def test_quantity_difference_is_not_called_a_mismatch_without_history_coverage() -> None:
    transactions = (OptionTransaction("t1", "ABEVV153", "BTG", -6000, 0.48, -3349.04),)

    result = OptionsReconciliationEngine().reconcile(transactions, _portfolio("ABEVV153"))

    assert result.quantity_mismatches == ()
    assert result.quality_status == "VALIDATED"
    assert result.history_coverage[0].option_ticker == "ABEVV153"
    assert result.history_coverage[0].net_historical_quantity == -6000
    assert result.history_coverage[0].current_position_quantity == -7000
    assert result.history_coverage[0].position_alignment == "DIFFERENT"
    assert result.history_coverage[0].completeness == "UNKNOWN"


def test_canonical_ticker_variants_share_history_coverage() -> None:
    transactions = (
        OptionTransaction("t1", "ABEVV153", "BTG", -4000, 0.48, -1912.0),
        OptionTransaction("t2", "ABEVV153 ON", "BTG", -3000, 0.45, -1350.0),
    )

    result = OptionsReconciliationEngine().reconcile(
        transactions,
        _portfolio("ABEVV153 PN"),
    )

    assert len(result.history_coverage) == 1
    assert result.history_coverage[0].option_ticker == "ABEVV153"
    assert result.history_coverage[0].net_historical_quantity == -7000
    assert result.history_coverage[0].current_position_quantity == -7000
    assert result.history_coverage[0].position_alignment == "ALIGNED"


def test_completeness_requires_explicit_full_history_source_evidence() -> None:
    transactions = (
        OptionTransaction(
            "t1",
            "ABEVV153",
            "BTG",
            -7000,
            0.48,
            -3349.04,
            as_of=date(2026, 9, 11),
            source_ref="SOURCE-A",
        ),
    )

    unknown = OptionsReconciliationEngine().reconcile(
        transactions,
        _portfolio("ABEVV153"),
    )
    assert unknown.history_coverage[0].completeness == "UNKNOWN"

    complete = OptionsReconciliationEngine().reconcile(
        transactions,
        _portfolio("ABEVV153"),
        source_coverage=(
            TransactionSourceCoverage(
                source_ref="SOURCE-A",
                coverage_start=date(2026, 1, 1),
                coverage_end=date(2026, 9, 11),
                scope="FULL_HISTORY",
                completeness="COMPLETE",
            ),
        ),
    )
    assert complete.history_coverage[0].completeness == "COMPLETE"


def test_partial_source_evidence_marks_history_partial() -> None:
    transactions = (
        OptionTransaction(
            "t1",
            "ABEVV153",
            "BTG",
            -7000,
            0.48,
            -3349.04,
            as_of=date(2026, 9, 11),
            source_ref="SOURCE-A",
        ),
    )

    result = OptionsReconciliationEngine().reconcile(
        transactions,
        _portfolio("ABEVV153"),
        source_coverage=(
            TransactionSourceCoverage(
                source_ref="SOURCE-A",
                coverage_start=date(2026, 9, 1),
                coverage_end=date(2026, 9, 11),
                scope="PERIOD_ONLY",
                completeness="PARTIAL",
            ),
        ),
    )
    assert result.history_coverage[0].completeness == "PARTIAL"


def test_cross_source_duplicate_detection_uses_typed_provenance() -> None:
    transactions = (
        OptionTransaction(
            "xlsx-1",
            "EQTLV369",
            "BTG",
            -1000,
            0.63,
            -634.89,
            as_of=date(2026, 9, 17),
            source_ref="Options Transactions XLSX",
            source_type="OPTIONS_XLSX",
            source_id="options.xlsx",
        ),
        OptionTransaction(
            "note-1",
            "EQTLV369",
            "BTG Pactual",
            -1000,
            0.63,
            -634.89,
            as_of=date(2026, 9, 17),
            source_ref="BTG:NotaCorretagem:34515456",
            note_number="34515456",
            source_type="BROKERAGE_NOTE",
            source_id="34515456",
        ),
    )

    result = OptionsReconciliationEngine().reconcile(
        transactions,
        _portfolio("EQTLV369"),
    )

    assert result.potential_cross_source_duplicates == ()
    assert result.matches == (
        ReconciliationMatch(
            status="RECONCILED",
            excel_transaction_id="xlsx-1",
            brokerage_transaction_id="note-1",
            reason="same ticker, signed quantity, execution price and total amount",
        ),
    )
