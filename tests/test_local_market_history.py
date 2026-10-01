from datetime import date, datetime, timezone

from b3_agent.providers.local_market_history import LocalFirstMarketDataAdapter
from b3_agent.providers.http_retry import ProviderRequestError
from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.schemas.market import StockMarketData


class RecordingProvider:
    def __init__(self, records=None, error=None):
        self.calls = []
        self.records = records or []
        self.error = error

    def get_market_data(self, ticker, start, end):
        self.calls.append((ticker, start, end))
        if self.error:
            raise self.error
        return [record for record in self.records if start <= record.observation_timestamp.date() <= end]


def record(day, source="b3_cotahist", close=30.0):
    observed = datetime(day.year, day.month, day.day, 21, tzinfo=timezone.utc)
    return StockMarketData(
        instrument_id="PETR4",
        ticker="PETR4",
        observation_timestamp=observed,
        available_timestamp=observed,
        source=source,
        ingested_at=observed,
        source_record_id=f"PETR4:{day.isoformat()}",
        quality_flags=("UNADJUSTED",) if source == "b3_cotahist" else (),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
        currency="BRL",
    )


def adapter(tmp_path, provider):
    return LocalFirstMarketDataAdapter(
        archive_dir=tmp_path / "archive",
        brapi_cache_dir=tmp_path / "brapi",
        brapi_provider=provider,
    )


def test_local_archive_covers_requested_range_without_brapi(tmp_path):
    provider = RecordingProvider()
    repository = MarketDataRepository(tmp_path / "archive")
    repository.write([record(date(2026, 9, 1)), record(date(2026, 9, 25))])

    rows = adapter(tmp_path, provider).get_market_data(
        "PETR4", date(2026, 9, 1), date(2026, 9, 25)
    )

    assert [row.source for row in rows] == ["b3_cotahist", "b3_cotahist"]
    assert provider.calls == []


def test_brapi_is_requested_only_after_local_coverage(tmp_path):
    brapi_record = record(date(2026, 9, 28), source="brapi", close=31.0)
    provider = RecordingProvider([brapi_record])
    repository = MarketDataRepository(tmp_path / "archive")
    repository.write([record(date(2026, 9, 1)), record(date(2026, 9, 25))])

    rows = adapter(tmp_path, provider).get_market_data(
        "PETR4", date(2026, 9, 1), date(2026, 9, 28)
    )

    assert provider.calls == [("PETR4", date(2026, 9, 26), date(2026, 9, 28))]
    assert [row.source for row in rows] == ["b3_cotahist", "b3_cotahist", "brapi"]
    assert rows[-1].close == 31.0


def test_old_archive_does_not_suppress_brapi_for_uncovered_window(tmp_path):
    provider = RecordingProvider([record(date(2026, 9, 25), source="brapi")])
    repository = MarketDataRepository(tmp_path / "archive")
    repository.write([record(date(2025, 12, 30))])

    rows = adapter(tmp_path, provider).get_market_data(
        "PETR4", date(2026, 9, 1), date(2026, 9, 28)
    )

    assert provider.calls == [("PETR4", date(2026, 9, 1), date(2026, 9, 28))]
    assert len(rows) == 1
    assert rows[0].source == "brapi"


def test_local_history_survives_no_new_brapi_quote(tmp_path):
    provider = RecordingProvider(error=ValueError("no new data"))
    repository = MarketDataRepository(tmp_path / "archive")
    repository.write([record(date(2026, 9, 1)), record(date(2026, 9, 25))])

    rows = adapter(tmp_path, provider).get_market_data(
        "PETR4", date(2026, 9, 1), date(2026, 9, 28)
    )

    assert len(rows) == 2
    assert rows[-1].source == "b3_cotahist"


def test_local_history_survives_wrapped_provider_request_failure(tmp_path):
    provider = RecordingProvider(error=ProviderRequestError("brapi request failed"))
    repository = MarketDataRepository(tmp_path / "archive")
    repository.write([record(date(2026, 9, 1)), record(date(2026, 9, 25))])

    rows = adapter(tmp_path, provider).get_market_data(
        "PETR4", date(2026, 9, 1), date(2026, 9, 28)
    )

    assert len(rows) == 2
    assert rows[-1].source == "b3_cotahist"


def test_oplab_precedes_brapi_when_local_archive_is_empty(tmp_path):
    oplab = RecordingProvider([
        record(date(2026, 9, 28), source="oplab", close=32.0)
    ])
    brapi = RecordingProvider([
        record(date(2026, 9, 28), source="brapi", close=31.0)
    ])
    service = LocalFirstMarketDataAdapter(
        archive_dir=tmp_path / "archive",
        brapi_cache_dir=tmp_path / "brapi",
        brapi_provider=brapi,
        oplab_provider=oplab,
    )

    rows = service.get_market_data(
        "PETR4", date(2026, 9, 28), date(2026, 9, 28)
    )

    assert len(rows) == 1
    assert rows[0].source == "oplab"
    assert rows[0].close == 32.0
    assert oplab.calls == [("PETR4", date(2026, 9, 28), date(2026, 9, 28))]
    assert brapi.calls == []


def test_brapi_is_fallback_when_oplab_market_history_fails(tmp_path):
    oplab = RecordingProvider(error=ValueError("oplab unavailable"))
    brapi = RecordingProvider([
        record(date(2026, 9, 28), source="brapi", close=31.0)
    ])
    service = LocalFirstMarketDataAdapter(
        archive_dir=tmp_path / "archive",
        brapi_cache_dir=tmp_path / "brapi",
        brapi_provider=brapi,
        oplab_provider=oplab,
    )

    rows = service.get_market_data(
        "PETR4", date(2026, 9, 28), date(2026, 9, 28)
    )

    assert len(rows) == 1
    assert rows[0].source == "brapi"
    assert oplab.calls == [("PETR4", date(2026, 9, 28), date(2026, 9, 28))]
    assert brapi.calls == [("PETR4", date(2026, 9, 28), date(2026, 9, 28))]
