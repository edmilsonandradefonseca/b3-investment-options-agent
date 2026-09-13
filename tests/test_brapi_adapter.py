from datetime import date
from datetime import datetime

import pytest

from b3_agent.providers.brapi.adapter import BrapiAdapter


def test_adapter_name():
    adapter = BrapiAdapter()

    assert adapter.name == "brapi"


def test_empty_ticker_is_rejected():
    adapter = BrapiAdapter()

    with pytest.raises(ValueError, match="ticker must not be empty"):
        adapter.get_market_data(
            "",
            date(2026, 9, 1),
            date(2026, 9, 10),
        )


def test_invalid_date_range_is_rejected():
    adapter = BrapiAdapter()

    with pytest.raises(
        ValueError,
        match="start date must be on or before end date",
    ):
        adapter.get_market_data(
            "PETR4",
            date(2026, 9, 10),
            date(2026, 9, 1),
        )


def test_response_without_results_is_rejected(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return b'{"results": []}'

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    adapter = BrapiAdapter()

    with pytest.raises(
        ValueError,
        match="brapi returned no market data",
    ):
        adapter.get_market_data(
            "PETR4",
            date(2026, 9, 1),
            date(2026, 9, 10),
        )


def test_historical_data_is_mapped_to_data_contract(monkeypatch):
    timestamp = 1788978600

    payload = {
        "results": [
            {
                "symbol": "PETR4",
                "data": {
                    "historicalDataPrice": [
                        {
                            "date": timestamp,
                            "open": 48.50,
                            "high": 49.12,
                            "low": 48.09,
                            "close": 49.00,
                            "volume": 27610000,
                        }
                    ]
                },
            }
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return __import__("json").dumps(payload).encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    adapter = BrapiAdapter()

    data = adapter.get_market_data(
        "petr4",
        date(2026, 9, 1),
        date(2026, 9, 10),
    )

    assert len(data) == 1

    record = data[0]

    assert record.ticker == "PETR4"
    assert record.instrument_id == "PETR4"
    assert record.open == 48.50
    assert record.high == 49.12
    assert record.low == 48.09
    assert record.close == 49.00
    assert record.volume == 27610000.0
    assert record.currency == "BRL"
    assert record.source == "brapi"
    assert isinstance(record.observation_timestamp, datetime)
    assert isinstance(record.available_timestamp, datetime)
    assert isinstance(record.ingested_at, datetime)
    assert record.source_record_id == f"PETR4:{timestamp}"


def test_missing_historical_field_is_rejected(monkeypatch):
    payload = {
        "results": [
            {
                "symbol": "PETR4",
                "data": {
                    "historicalDataPrice": [
                        {
                            "date": 1788978600,
                            "open": 48.50,
                            "high": 49.12,
                            "low": 48.09,
                            "close": 49.00,
                            # volume intentionally missing
                        }
                    ]
                },
            }
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return __import__("json").dumps(payload).encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    adapter = BrapiAdapter()

    with pytest.raises(
        ValueError,
        match="missing required fields",
    ):
        adapter.get_market_data(
            "PETR4",
            date(2026, 9, 1),
            date(2026, 9, 10),
        )


def test_empty_historical_data_is_rejected(monkeypatch):
    payload = {
        "results": [
            {
                "symbol": "PETR4",
                "data": {
                    "historicalDataPrice": []
                },
            }
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return __import__("json").dumps(payload).encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    adapter = BrapiAdapter()

    with pytest.raises(
        ValueError,
        match="no historical data",
    ):
        adapter.get_market_data(
            "PETR4",
            date(2026, 9, 1),
            date(2026, 9, 10),
        )
