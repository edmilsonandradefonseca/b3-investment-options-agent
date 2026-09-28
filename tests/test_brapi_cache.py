from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import os

import pytest

from b3_agent.providers.brapi.cache import CachedBrapiAdapter
from b3_agent.schemas.market import StockMarketData


class CountingProvider:
    def __init__(self):
        self.calls = []

    def get_market_data(self, ticker, start, end):
        self.calls.append((ticker, start, end))
        observed = datetime(2026, 9, 25, 20, tzinfo=timezone.utc)
        return [StockMarketData(
            instrument_id=ticker, ticker=ticker,
            observation_timestamp=observed, available_timestamp=observed,
            source="brapi", ingested_at=observed,
            source_record_id=f"{ticker}:2026-09-25", open=29, high=30,
            low=28, close=29.5, volume=1000,
        )]


def test_cache_skips_repeat_provider_calls_across_adapter_instances(tmp_path):
    provider = CountingProvider()
    start, end = date(2026, 9, 24), date(2026, 9, 28)
    first = CachedBrapiAdapter(tmp_path, provider)
    assert len(first.get_market_data("petr4", start, end)) == 1
    second = CachedBrapiAdapter(tmp_path, provider)
    assert len(second.get_market_data("PETR4", start, end)) == 1
    assert provider.calls == [("PETR4", start, end)]


def test_expired_cache_refreshes_only_recent_window(tmp_path):
    provider = CountingProvider()
    start, end = date(2026, 9, 1), date(2026, 9, 28)
    cache = CachedBrapiAdapter(tmp_path, provider)
    latest = cache.get_market_data("PETR4", start, end)[0]
    first_day = datetime(2026, 9, 2, 20, tzinfo=timezone.utc)
    cache.repository.write([
        replace(latest, observation_timestamp=first_day, source_record_id="PETR4:2026-09-02"),
        latest,
    ])
    path = tmp_path / "ticker=PETR4" / "market.parquet"
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
    os.utime(path, (old, old))
    assert len(cache.get_market_data("PETR4", start, end)) == 2
    assert len(provider.calls) == 2
    assert provider.calls[1][1] == date(2026, 9, 20)
    assert provider.calls[1][2] == end


def test_expired_cache_does_not_serve_old_price_when_provider_fails(tmp_path):
    provider = CountingProvider()
    cache = CachedBrapiAdapter(tmp_path, provider)
    cache.get_market_data("PETR4", date(2026, 9, 24), date(2026, 9, 28))
    path = tmp_path / "ticker=PETR4" / "market.parquet"
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
    os.utime(path, (old, old))

    def failed(*args):
        raise OSError("provider unavailable")

    provider.get_market_data = failed
    with pytest.raises(OSError, match="provider unavailable"):
        cache.get_market_data("PETR4", date(2026, 9, 24), date(2026, 9, 28))
