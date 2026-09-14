import math
import pytest
from datetime import datetime, timedelta, timezone

from b3_agent.quant_engine import compute_quant_features
from b3_agent.schemas.market import StockMarketData


def make_records(prices):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    return [
        StockMarketData(
            instrument_id="TEST4",
            ticker="TEST4",
            observation_timestamp=start + timedelta(days=i),
            available_timestamp=start + timedelta(days=i),
            source="test",
            ingested_at=start + timedelta(days=i),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=1000.0,
        )
        for i, price in enumerate(prices)
    ]


def test_quant_engine_basic_metrics():
    records = make_records([100, 101, 102, 103, 104])

    result = compute_quant_features(records)

    assert result.ticker == "TEST4"
    assert result.data_points == 5
    assert result.return_1d == 104 / 103 - 1
    assert result.log_return_1d is not None
    assert result.max_drawdown == 0.0
    assert result.average_volume_20d == 1000.0
    assert result.average_dollar_volume_20d == 102000.0
    assert result.sma_20 is None
    assert result.completeness_score == 1.0


def test_quant_engine_sma_20():
    prices = list(range(1, 21))
    records = make_records(prices)

    result = compute_quant_features(records)

    assert result.sma_20 == 10.5


def test_quant_engine_drawdown():
    records = make_records([100, 110, 90, 95, 120])

    result = compute_quant_features(records)

    assert result.max_drawdown == 90 / 110 - 1


def test_quant_engine_adjusted_close():
    records = make_records([100, 110, 120])

    records[-1] = StockMarketData(
        instrument_id="TEST4",
        ticker="TEST4",
        observation_timestamp=records[-1].observation_timestamp,
        available_timestamp=records[-1].available_timestamp,
        source="test",
        ingested_at=records[-1].ingested_at,
        open=120,
        high=120,
        low=120,
        close=120,
        adjusted_close=100,
        volume=1000,
    )

    result = compute_quant_features(records)

    assert result.return_1d == 100 / 110 - 1

def test_return_1d_is_none_when_latest_observation_has_gap():
    records = [
        StockMarketData(instrument_id="ITUB4", ticker="ITUB4", observation_timestamp=datetime.fromisoformat("2026-09-01T10:00:00"), available_timestamp=datetime.fromisoformat("2026-09-01T10:00:00"), source="TEST", ingested_at=datetime.fromisoformat("2026-09-01T10:00:00"), open=100.0, high=100.0, low=100.0, close=100.0, volume=1000.0),
        StockMarketData(instrument_id="ITUB4", ticker="ITUB4", observation_timestamp=datetime.fromisoformat("2026-09-02T10:00:00"), available_timestamp=datetime.fromisoformat("2026-09-02T10:00:00"), source="TEST", ingested_at=datetime.fromisoformat("2026-09-02T10:00:00"), open=105.0, high=105.0, low=105.0, close=105.0, volume=1000.0),
        StockMarketData(instrument_id="ITUB4", ticker="ITUB4", observation_timestamp=datetime.fromisoformat("2026-09-04T10:00:00"), available_timestamp=datetime.fromisoformat("2026-09-04T10:00:00"), source="TEST", ingested_at=datetime.fromisoformat("2026-09-04T10:00:00"), open=110.0, high=110.0, low=110.0, close=110.0, volume=1000.0),
    ]

    features = compute_quant_features(records)

    assert features.return_1d is None
    assert features.log_return_1d is None


def test_return_1d_uses_immediately_previous_observation():
    records = [
        StockMarketData(instrument_id="ITUB4", ticker="ITUB4", observation_timestamp=datetime.fromisoformat("2026-09-01T10:00:00"), available_timestamp=datetime.fromisoformat("2026-09-01T10:00:00"), source="TEST", ingested_at=datetime.fromisoformat("2026-09-01T10:00:00"), open=100.0, high=100.0, low=100.0, close=100.0, volume=1000.0),
        StockMarketData(instrument_id="ITUB4", ticker="ITUB4", observation_timestamp=datetime.fromisoformat("2026-09-02T10:00:00"), available_timestamp=datetime.fromisoformat("2026-09-02T10:00:00"), source="TEST", ingested_at=datetime.fromisoformat("2026-09-02T10:00:00"), open=105.0, high=105.0, low=105.0, close=105.0, volume=1000.0),
    ]

    features = compute_quant_features(records)

    assert features.return_1d == pytest.approx(0.05)
    assert features.log_return_1d == pytest.approx(math.log(1.05))
