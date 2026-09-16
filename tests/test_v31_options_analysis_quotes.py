from datetime import date, datetime, timezone

from b3_agent.options.analysis import OptionsAnalysisEngine
from b3_agent.schemas.option import OptionContract, OptionQuote


def make_quote(option_id: str, *, mid: float | None = 2.0) -> OptionQuote:
    now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    return OptionQuote(
        instrument_id=option_id,
        ticker=option_id,
        observation_timestamp=now,
        available_timestamp=now,
        source="oplab",
        ingested_at=now,
        option_id=option_id,
        bid=1.9 if mid is not None else None,
        ask=2.1 if mid is not None else None,
        last=2.0 if mid is not None else None,
        mid=mid,
        volume=100.0,
        open_interest=500.0,
    )


def test_analyze_quotes_routes_put_and_call_to_deterministic_engines():
    contracts = (
        OptionContract(
            option_id="PUT1",
            underlying_id="PETR4",
            underlying_ticker="PETR4",
            option_ticker="PETR4P300",
            option_type="PUT",
            strike=30.0,
            expiration_date=date(2026, 10, 16),
        ),
        OptionContract(
            option_id="CALL1",
            underlying_id="PETR4",
            underlying_ticker="PETR4",
            option_ticker="PETR4C300",
            option_type="CALL",
            strike=30.0,
            expiration_date=date(2026, 10, 16),
        ),
    )
    result = OptionsAnalysisEngine().analyze_quotes(
        contracts=contracts,
        quotes=(make_quote("PUT1"), make_quote("CALL1")),
        as_of=date(2026, 9, 16),
        current_prices={"PETR4": 28.0},
        source_refs=("oplab",),
    )

    assert len(result.puts) == 1
    assert len(result.calls) == 1
    assert result.puts[0].effective_price == 28.0
    assert result.calls[0].action == "SELL_CALL"
    assert result.source_refs == ("oplab",)
    assert result.quality_status == "VALIDATED"


def test_analyze_quotes_uses_bid_ask_when_mid_and_last_are_missing():
    contract = OptionContract(
        option_id="PUT2",
        underlying_id="VALE3",
        underlying_ticker="VALE3",
        option_ticker="VALE3P500",
        option_type="P",
        strike=50.0,
        expiration_date=date(2026, 10, 16),
    )
    quote = make_quote("PUT2", mid=None)
    result = OptionsAnalysisEngine().analyze_quotes(
        contracts=(contract,),
        quotes=(quote,),
        as_of=date(2026, 9, 16),
    )

    assert len(result.puts) == 1
    assert result.puts[0].premium == 2.0


def test_analyze_quotes_rejects_call_without_current_price():
    contract = OptionContract(
        option_id="CALL2",
        underlying_id="ITUB4",
        underlying_ticker="ITUB4",
        option_ticker="ITUB4C400",
        option_type="C",
        strike=40.0,
        expiration_date=date(2026, 10, 16),
    )
    result = OptionsAnalysisEngine().analyze_quotes(
        contracts=(contract,),
        quotes=(make_quote("CALL2"),),
        as_of=date(2026, 9, 16),
    )

    assert result.calls == ()
    assert result.quality_status == "WARNING"
    assert result.assumptions == {"rejected_quotes": ("missing_current_price:CALL2",)}
