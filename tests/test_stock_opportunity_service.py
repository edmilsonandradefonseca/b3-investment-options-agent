from datetime import date, datetime

import pytest

from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.valuation import ValuationRange
from b3_agent.stock_opportunity_service import StockOpportunityService


AS_OF = date(2026, 9, 11)


def market_record(ticker: str, timestamp: datetime, close: float) -> StockMarketData:
    return StockMarketData(
        instrument_id=ticker,
        ticker=ticker,
        observation_timestamp=timestamp,
        available_timestamp=timestamp,
        source="brapi",
        ingested_at=timestamp,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000_000,
    )


def valuation() -> ValuationRange:
    return ValuationRange(
        instrument_id="ITUB4",
        ticker="ITUB4",
        as_of=AS_OF,
        method="PE",
        bear_value=15.0,
        base_value=20.0,
        bull_value=25.0,
        accumulation_price=16.0,
        reduce_price=20.0,
        sell_price=25.0,
        source_refs=("fundamentals:itub4",),
        quality_status="VALIDATED",
    )


def test_produces_accumulate_from_latest_point_in_time_market_price():
    records = [
        market_record("ITUB4", datetime(2026, 9, 10, 18), 18.0),
        market_record("ITUB4", datetime(2026, 9, 11, 18), 15.5),
    ]

    result = StockOpportunityService().produce(
        records,
        valuation(),
        as_of=datetime(2026, 9, 11, 23, 59),
    )

    assert len(result) == 1
    assert result[0].ticker == "ITUB4"
    assert result[0].action == "ACCUMULATE"
    assert result[0].expected_return == pytest.approx((20.0 / 15.5) - 1.0)
    assert "brapi" in result[0].source_refs
    assert result[0].quant_features_ref == "quant:ITUB4:2026-09-11 23:59:00"


def test_excludes_future_market_observation():
    records = [
        market_record("ITUB4", datetime(2026, 9, 10, 18), 18.0),
        market_record("ITUB4", datetime(2026, 9, 11, 18), 30.0),
    ]

    result = StockOpportunityService().produce(
        records,
        valuation(),
        as_of=datetime(2026, 9, 10, 23, 59),
    )

    assert len(result) == 1
    assert result[0].action == "BUY"
    assert result[0].expected_return == pytest.approx((20.0 / 18.0) - 1.0)


def test_rejects_empty_market_data():
    with pytest.raises(ValueError, match="records must not be empty"):
        StockOpportunityService().produce([], valuation())


def test_rejects_when_no_market_observation_is_available_at_decision_time():
    records = [
        market_record("ITUB4", datetime(2026, 9, 12, 18), 15.0),
    ]

    with pytest.raises(
        ValueError,
        match="no stock market observations are available at decision timestamp",
    ):
        StockOpportunityService().produce(
            records,
            valuation(),
            as_of=datetime(2026, 9, 11, 23, 59),
        )


def test_rejects_non_positive_latest_close():
    records = [
        market_record("ITUB4", datetime(2026, 9, 11, 18), 0.0),
    ]

    with pytest.raises(ValueError, match="latest market close must be positive"):
        StockOpportunityService().produce(records, valuation(), as_of=AS_OF)
