from datetime import datetime
import json

import pytest

from b3_agent.providers.brapi.adapter import BrapiAdapter


def test_adapter_name():
    adapter = BrapiAdapter()

    assert adapter.name == "brapi"


def test_empty_ticker_is_rejected():
    adapter = BrapiAdapter()

    with pytest.raises(ValueError, match="ticker must not be empty"):
        adapter.get_market_data("")


def test_response_without_results_is_rejected(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return json.dumps({"results": []}).encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    adapter = BrapiAdapter()

    with pytest.raises(
        ValueError,
        match="brapi returned no market data",
    ):
        adapter.get_market_data("PETR4")


def test_missing_required_field_is_rejected(monkeypatch):
    payload = {
        "results": [
            {
                "regularMarketOpen": 48.50,
                "regularMarketDayHigh": 49.12,
                "regularMarketDayLow": 48.09,
                "regularMarketPrice": 49.00,
                # volume intentionally missing
            }
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    adapter = BrapiAdapter()

    with pytest.raises(
        ValueError,
        match="missing required fields",
    ):
        adapter.get_market_data("PETR4")


def test_market_data_is_mapped_to_data_contract(monkeypatch):
    payload = {
        "results": [
            {
                "regularMarketOpen": 48.50,
                "regularMarketDayHigh": 49.12,
                "regularMarketDayLow": 48.09,
                "regularMarketPrice": 49.00,
                "regularMarketVolume": 27610000,
            }
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    adapter = BrapiAdapter()
    data = adapter.get_market_data("petr4")

    assert data.ticker == "PETR4"
    assert data.instrument_id == "PETR4"
    assert data.open == 48.50
    assert data.high == 49.12
    assert data.low == 48.09
    assert data.close == 49.00
    assert data.volume == 27610000.0
    assert data.currency == "BRL"
    assert data.source == "brapi"
    assert isinstance(data.observation_timestamp, datetime)
    assert isinstance(data.available_timestamp, datetime)
    assert isinstance(data.ingested_at, datetime)