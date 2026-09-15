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


def test_btg_quantity_wins_and_creates_warning_on_mismatch() -> None:
    transactions = (OptionTransaction("t1", "ABEVV153", "BTG", -6000, 0.48, -3349.04),)

    result = OptionsReconciliationEngine().reconcile(transactions, _portfolio("ABEVV153"))

    assert result.quantity_mismatches == (("ABEVV153", -6000, -7000),)
    assert result.quality_status == "WARNING"
