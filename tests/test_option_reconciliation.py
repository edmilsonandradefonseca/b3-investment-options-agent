from datetime import date

from b3_agent.options.reconciliation import OptionsReconciliationEngine
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
