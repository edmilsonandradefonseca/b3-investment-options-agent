from datetime import datetime, timedelta, timezone

from b3_agent.quant_engine import compute_quant_features
from b3_agent.schemas.market import StockMarketData


def make_series(prices, ticker):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    return [
        StockMarketData(
            instrument_id=ticker,
            ticker=ticker,
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


def test_beta_and_correlation_perfect_positive():
    benchmark = make_series([100, 110, 121, 133.1, 146.41], "IBOV")
    asset = make_series([50, 55, 60.5, 66.55, 73.205], "TEST4")

    result = compute_quant_features(
        asset,
        benchmark_records=benchmark,
    )

    assert result.beta is not None
    assert result.correlation is not None
    assert abs(result.beta - 1.0) < 1e-10
    assert abs(result.correlation - 1.0) < 1e-10


def test_beta_and_correlation_require_aligned_data():
    benchmark = make_series([100, 110, 121], "IBOV")
    asset = make_series([50, 55], "TEST4")

    result = compute_quant_features(
        asset,
        benchmark_records=benchmark,
    )

    assert result.beta is None
    assert result.correlation is None


def test_without_benchmark_metrics_are_none():
    asset = make_series([50, 55, 60], "TEST4")

    result = compute_quant_features(asset)

    assert result.beta is None
    assert result.correlation is None


def test_benchmark_is_not_fetched_by_quant_engine():
    asset = make_series([50, 55, 60], "TEST4")

    result = compute_quant_features(
        asset,
        benchmark_records=[],
    )

    assert result.beta is None
    assert result.correlation is None
from datetime import datetime, timedelta, timezone

from b3_agent.quant_engine import _aligned_returns, _beta, _correlation
from b3_agent.schemas.market import StockMarketData


def record(ticker, day, price):
    timestamp = datetime(2026, 1, day, tzinfo=timezone.utc)
    return StockMarketData(
        instrument_id=ticker,
        ticker=ticker,
        observation_timestamp=timestamp,
        available_timestamp=timestamp,
        source="test",
        ingested_at=timestamp,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1000,
    )


def test_alignment_uses_common_dates_only():
    asset = [
        record("TEST4", 1, 100),
        record("TEST4", 2, 110),
        record("TEST4", 3, 121),
        record("TEST4", 4, 133.1),
    ]

    benchmark = [
        record("IBOV", 1, 100),
        record("IBOV", 2, 105),
        record("IBOV", 4, 115),
        record("IBOV", 5, 120),
    ]

    asset_returns, benchmark_returns = _aligned_returns(
        asset,
        benchmark,
    )

    assert len(asset_returns) == 2
    assert len(benchmark_returns) == 2


def test_beta_and_correlation_are_none_for_insufficient_common_dates():
    asset = [
        record("TEST4", 1, 100),
        record("TEST4", 2, 110),
    ]

    benchmark = [
        record("IBOV", 1, 100),
        record("IBOV", 3, 105),
    ]

    asset_returns, benchmark_returns = _aligned_returns(
        asset,
        benchmark,
    )

    assert _beta(asset_returns, benchmark_returns) is None
    assert _correlation(asset_returns, benchmark_returns) is None
