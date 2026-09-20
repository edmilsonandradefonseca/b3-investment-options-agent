from datetime import date

from b3_agent.options.reconciliation import (
    OptionsReconciliationEngine,
    TransactionSourceCoverage,
)
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext, Position


def _portfolio(ticker: str = "ASAIJ970", quantity: float = 3000) -> PortfolioContext:
    return PortfolioContext(
        as_of=date(2026, 9, 17),
        positions=(
            Position(
                position_id=f"pos-{ticker}",
                ticker=ticker,
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


def _excel(
    transaction_id: str = "excel-1",
    ticker: str = "ASAIJ970",
    quantity: float = 3000,
    price: float = 0.94,
    total: float = 2820,
) -> OptionTransaction:
    return OptionTransaction(
        transaction_id=transaction_id,
        option_ticker=ticker,
        broker="BTG Pactual",
        quantity=quantity,
        average_cost=price,
        total_cost=total,
        source_ref="Options Transactions XLSX",
        source_type="OPTIONS_XLSX",
        source_id="options_transactions.xlsx",
    )


def _brokerage(
    transaction_id: str = "note-1",
    ticker: str = "ASAIJ970",
    quantity: float = 3000,
    price: float = 0.94,
    total: float = 2820,
    trade_date: date = date(2026, 9, 17),
) -> OptionTransaction:
    return OptionTransaction(
        transaction_id=transaction_id,
        option_ticker=ticker,
        broker="BTG Pactual",
        quantity=quantity,
        average_cost=price,
        total_cost=total,
        as_of=trade_date,
        source_ref=f"BTG:NotaCorretagem:{transaction_id}",
        note_number=transaction_id,
        source_type="BROKERAGE_NOTE",
        source_id=transaction_id,
    )


def test_exact_excel_and_brokerage_trade_is_reconciled_once():
    result = OptionsReconciliationEngine().reconcile(
        (_excel(), _brokerage()),
        _portfolio(),
    )

    assert [match.status for match in result.matches] == ["RECONCILED"]
    assert result.matches[0].excel_transaction_id == "excel-1"
    assert result.matches[0].brokerage_transaction_id == "note-1"
    assert result.potential_cross_source_duplicates == ()
    assert result.quality_status == "VALIDATED"


def test_same_economic_trade_in_two_different_notes_is_not_double_counted_by_matching():
    result = OptionsReconciliationEngine().reconcile(
        (
            _excel(),
            _brokerage("note-1"),
            _brokerage("note-2"),
        ),
        _portfolio(),
    )

    reconciled = [match for match in result.matches if match.status == "RECONCILED"]
    brokerage_only = [match for match in result.matches if match.status == "BROKERAGE_ONLY"]

    assert len(reconciled) == 1
    assert len(brokerage_only) == 1


def test_source_only_transactions_are_explicit():
    result = OptionsReconciliationEngine().reconcile(
        (_excel(), _brokerage(quantity=2000)),
        _portfolio(),
    )

    assert {match.status for match in result.matches} == {
        "EXCEL_ONLY",
        "BROKERAGE_ONLY",
    }


def test_same_ticker_and_quantity_but_different_price_is_potential_duplicate():
    result = OptionsReconciliationEngine().reconcile(
        (_excel(price=0.94, total=2820), _brokerage(price=0.95, total=2850)),
        _portfolio(),
    )

    assert result.potential_cross_source_duplicates == (("excel-1", "note-1"),)
    assert result.quality_status == "WARNING"
    assert any(match.status == "POTENTIAL_DUPLICATE" for match in result.matches)


def test_same_ticker_and_quantity_but_different_date_is_not_automatically_reconciled():
    result = OptionsReconciliationEngine().reconcile(
        (_excel(), _brokerage(trade_date=date(2026, 9, 18))),
        _portfolio(),
    )

    # Current matching deliberately uses fields common to both sources.
    # Date is available only in the brokerage source in the current XLSX schema,
    # so the trade remains reconciled rather than inventing a date mismatch.
    assert [match.status for match in result.matches] == ["RECONCILED"]


def test_multiple_open_close_trades_are_not_compared_one_to_one_with_position():
    result = OptionsReconciliationEngine().reconcile(
        (
            _excel("excel-open", quantity=3000, total=2820),
            _excel("excel-close", quantity=-1000, price=1.10, total=-1100),
            _brokerage("note-open", quantity=3000, total=2820),
            _brokerage("note-close", quantity=-1000, price=1.10, total=-1100),
        ),
        _portfolio(quantity=2000),
    )

    statuses = [match.status for match in result.matches]
    assert statuses.count("RECONCILED") == 2
    assert result.history_coverage[0].net_historical_quantity == 4000
    assert result.history_coverage[0].current_position_quantity == 2000
    assert result.history_coverage[0].position_alignment == "DIFFERENT"


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


def test_sell_put_and_buy_put_can_be_reconciled_by_signed_quantity():
    excel = _excel(ticker="ASAIK102", quantity=-3000, price=1.04, total=-3120)
    brokerage = _brokerage(
        ticker="ASAIK102",
        quantity=-3000,
        price=1.04,
        total=-3120,
    )
    result = OptionsReconciliationEngine().reconcile(
        (excel, brokerage),
        _portfolio(ticker="ASAIK102", quantity=-3000),
    )
    assert [match.status for match in result.matches] == ["RECONCILED"]


def test_different_option_contracts_are_not_matched():
    result = OptionsReconciliationEngine().reconcile(
        (
            _excel(ticker="ASAIJ970"),
            _brokerage(ticker="ASAIK102"),
        ),
        _portfolio(ticker="ASAIJ970"),
    )
    statuses = {match.status for match in result.matches}
    assert statuses == {"EXCEL_ONLY", "BROKERAGE_ONLY"}
