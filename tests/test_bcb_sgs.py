from __future__ import annotations

from datetime import date
import json

import pytest

from b3_agent.providers.bcb_sgs import BcbSgsAdapter


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_sgs_series_maps_to_macro_observation(monkeypatch):
    payload = [
        {"data": "25/09/2026", "valor": "14.90"},
        {"data": "26/09/2026", "valor": "14.90"},
    ]
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    records = BcbSgsAdapter().get_series(
        "SELIC",
        start=date(2026, 9, 1),
        end=date(2026, 9, 27),
    )

    assert len(records) == 2
    assert records[0].indicator == "SELIC"
    assert records[0].value == 14.90
    assert records[0].unit == "percent_per_year"
    assert records[0].source == "bcb_sgs"
    assert records[0].source_record_id == "sgs:1178:2026-09-25"
    assert records[0].quality_flags == ("availability_is_ingestion_time",)


def test_latest_selects_most_recent_observation(monkeypatch):
    payload = [
        {"data": "01/09/2026", "valor": "0.05"},
        {"data": "26/09/2026", "valor": "0.06"},
    ]
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    result = BcbSgsAdapter().latest(
        "CDI",
        start=date(2026, 9, 1),
        end=date(2026, 9, 27),
    )

    assert result.indicator == "CDI"
    assert result.value == 0.06
    assert result.source_record_id == "sgs:12:2026-09-26"


def test_core_snapshot_requests_selic_cdi_ipca(monkeypatch):
    def fake_urlopen(request, timeout):
        url = request.full_url
        if ".1178/" in url:
            value = "14.90"
        elif ".12/" in url:
            value = "0.06"
        elif ".433/" in url:
            value = "0.35"
        else:
            raise AssertionError(url)
        return FakeResponse([{"data": "01/09/2026", "valor": value}])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    snapshot = BcbSgsAdapter().get_core_snapshot(
        start=date(2026, 8, 1),
        end=date(2026, 9, 27),
    )

    assert set(snapshot) == {"SELIC", "CDI", "IPCA"}
    assert snapshot["SELIC"].unit == "percent_per_year"
    assert snapshot["CDI"].unit == "percent_per_day"
    assert snapshot["IPCA"].unit == "percent_per_month"


def test_unsupported_indicator_is_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        BcbSgsAdapter().get_series(
            "USD",
            start=date(2026, 9, 1),
            end=date(2026, 9, 27),
        )
