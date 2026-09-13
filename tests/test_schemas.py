from datetime import date, datetime, timezone

from b3_agent.schemas import (
    CorporateAction,
    Instrument,
    MacroObservation,
    OptionContract,
    OptionQuote,
    StockFundamental,
    StockMarketData,
)


def now():
    return datetime.now(timezone.utc)


def test_instrument_schema():
    instrument = Instrument(
        instrument_id="B3-PETR4",
        ticker="PETR4",
        name="Petroleo Brasileiro S.A.",
        asset_type="STOCK",
        exchange="B3",
        currency="BRL",
    )

    assert instrument.ticker == "PETR4"
    assert instrument.asset_type == "STOCK"


def test_market_data_schema():
    record = StockMarketData(
        instrument_id="B3-PETR4",
        ticker="PETR4",
        observation_timestamp=now(),
        available_timestamp=now(),
        source="test",
        ingested_at=now(),
        open=35.0,
        high=36.0,
        low=34.5,
        close=35.5,
        volume=1000000,
    )

    assert record.close == 35.5
    assert record.currency == "BRL"


def test_fundamental_schema():
    record = StockFundamental(
        instrument_id="B3-PETR4",
        ticker="PETR4",
        observation_timestamp=now(),
        available_timestamp=now(),
        source="test",
        ingested_at=now(),
        metric="EBITDA",
        value=1000000000,
        period_end=date(2025, 12, 31),
        report_date=date(2026, 2, 20),
    )

    assert record.metric == "EBITDA"


def test_option_schema():
    contract = OptionContract(
        option_id="PETR4-OPT-35-C",
        underlying_id="B3-PETR4",
        underlying_ticker="PETR4",
        option_ticker="PETR4TEST",
        option_type="CALL",
        strike=35.0,
        expiration_date=date(2026, 10, 16),
    )

    quote = OptionQuote(
        instrument_id="PETR4TEST",
        ticker="PETR4TEST",
        observation_timestamp=now(),
        available_timestamp=now(),
        source="test",
        ingested_at=now(),
        option_id=contract.option_id,
        bid=1.0,
        ask=1.2,
        last=1.1,
        mid=1.1,
        volume=100,
        open_interest=500,
    )

    assert contract.strike == 35.0
    assert quote.open_interest == 500


def test_corporate_action_schema():
    record = CorporateAction(
        instrument_id="B3-PETR4",
        ticker="PETR4",
        observation_timestamp=now(),
        available_timestamp=now(),
        source="test",
        ingested_at=now(),
        action_type="DIVIDEND",
        ex_date=date(2026, 9, 10),
        amount=0.50,
        currency="BRL",
    )

    assert record.action_type == "DIVIDEND"


def test_macro_schema():
    record = MacroObservation(
        instrument_id="MACRO-SELIC",
        ticker="SELIC",
        observation_timestamp=now(),
        available_timestamp=now(),
        source="test",
        ingested_at=now(),
        indicator="SELIC",
        value=15.0,
        unit="percent",
    )

    assert record.indicator == "SELIC"
def test_stock_market_data_to_dict_includes_market_fields():
    from datetime import datetime, timezone

    from b3_agent.schemas.market import StockMarketData

    timestamp = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)

    data = StockMarketData(
        instrument_id="PETR4",
        ticker="PETR4",
        observation_timestamp=timestamp,
        available_timestamp=timestamp,
        source="brapi",
        ingested_at=timestamp,
        open=48.50,
        high=49.12,
        low=48.09,
        close=49.00,
        volume=27610000.0,
    )

    result = data.to_dict()

    assert result["ticker"] == "PETR4"
    assert result["open"] == 48.50
    assert result["high"] == 49.12
    assert result["low"] == 48.09
    assert result["close"] == 49.00
    assert result["volume"] == 27610000.0
    assert result["currency"] == "BRL"
    assert result["observation_timestamp"] == "2026-09-13T18:00:00+00:00"
