from datetime import date

from b3_agent.options.reconciliation import (
    OptionsReconciliationEngine,
    TransactionSourceCoverage,
)
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext, Position


def _portfolio(quantity: float = 3000) -> PortfolioContext:
    return PortfolioContext(
        as_of=date(2026, 9, 17),
        positions=(
            Position(
                position_id="pos-1",
                ticker="ASAIJ970",
                instrument_type="OPTION",
                quantity=quantity,
                average_cost=0.94,
                strike=9.70,
                expiration_date=date(2026, 10, 16),
                option_type="CALL",
                underlying_ticker="ASAI3",
                contract_multiplier=1,
            ),
        ),
    )


def _excel(quantity: float = 3000, price: float = 0.94, total: float = 2820) -> OptionTransaction:
    return OptionTransaction(
        transaction_id="excel-1",
        option_ticker="ASAIJ970",
        broker="BTG Pactual",
        quantity=quantity,
        average_cost=price,
        total_cost=total,
        source_ref="Options Transactions XLSX",
        source_type="OPTIONS_XLSX",
        source_id="options_transactions.xlsx",
    )


def _brokerage(quantity: float = 3000, price: float = 0.94, total: float = 2820) -> OptionTransaction:
    return OptionTransaction(
        transaction_id="note-1",
        option_ticker="ASAIJ970",
        broker="BTG Pactual",
        quantity=quantity,
        average_cost=price,
        total_cost=total,
        as_of=date(2026, 9, 17),
        source_ref="BTG:NotaCorretagem:34515456",
        note_number="34515456",
        source_type="BROKERAGE_NOTE",
        source_id="34515456",
    )


def test_exact_excel_and_brokerage_trade_is_reconciled_once():
    result = OptionsReconciliationEngine().reconcile(
        (_excel(), _brokerage()),
        _portfolio(),
    )

    assert len(result.matches) == 1
    assert result.matches[0].status == "RECONCILED"
    assert result.matches[0].excel_transaction_id == "excel-1"
    assert result.matches[0].brokerage_transaction_id == "note-1"
    assert result.potential_cross_source_duplicates == ()
    assert result.quality_status == "VALIDATED"


def test_source_only_transactions_are_explicit():
    result = OptionsReconciliationEngine().reconcile(
        (_excel(), _brokerage(quantity=2000)),
        _portfolio(),
    )

    assert {match.status for match in result.matches} == {
        "EXCEL_ONLY",
        "BROKERAGE_ONLY",
    }
    assert len(result.matches) == 2


def test_same_ticker_and_quantity_but_different_price_is_potential_duplicate():
    result = OptionsReconciliationEngine().reconcile(
        (_excel(price=0.94, total=2820), _brokerage(price=0.95, total=2850)),
        _portfolio(),
    )

    assert result.potential_cross_source_duplicates == (("excel-1", "note-1"),)
    assert result.quality_status == "WARNING"
    assert any(match.status == "POTENTIAL_DUPLICATE" for match in result.matches)


def test_complete_history_quantity_mismatch_is_explicit():
    transaction = _brokerage(quantity=2000)
    coverage = TransactionSourceCoverage(
        source_ref=transaction.source_ref,
        scope="FULL_HISTORY",
        completeness="COMPLETE",
    )

    result = OptionsReconciliationEngine().reconcile(
        (transaction,),
        _portfolio(quantity=3000),
        source_coverage=(coverage,),
    )

    assert result.quantity_mismatches == (("ASAIJ970", 2000, 3000),)
    assert result.history_coverage[0].completeness == "COMPLETE"
    assert result.history_coverage[0].position_alignment == "DIFFERENT"
    assert result.quality_status == "WARNING"
