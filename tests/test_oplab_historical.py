from __future__ import annotations

from datetime import date
import json
from unittest.mock import patch

from b3_agent.providers.oplab.historical import OplabHistoricalAdapter


def test_oplab_historical_maps_daily_ohlcv_and_sends_token():
    payload = {
        "symbol": "WEGE3",
        "name": "WEGE3",
        "resolution": "1d",
        "data": [
            {
                "time": 1790737200000,
                "open": 50.79,
                "high": 51.11,
                "low": 49.25,
                "close": 49.46,
                "volume": 8926600,
                "fvolume": 443753517,
            },
            {
                "time": 1790823600000,
                "open": 49.92,
                "high": 50.06,
                "low": 49.18,
                "close": 49.61,
                "volume": 3694500,
                "fvolume": 183220000,
            },
        ],
    }
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["token"] = request.headers.get("Access-token")

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return json.dumps(payload).encode()

        return Response()

    with patch.dict("os.environ", {"OPLAB_API_TOKEN": "secret-token"}), patch(
        "b3_agent.providers.oplab.historical.urllib.request.urlopen",
        side_effect=fake_urlopen,
    ):
        rows = OplabHistoricalAdapter().get_market_data(
            "wege3",
            date(2026, 9, 30),
            date(2026, 10, 1),
        )

    assert captured["token"] == "secret-token"
    assert "/market/historical/WEGE3/1d?" in captured["url"]
    assert len(rows) == 2
    assert rows[0].ticker == "WEGE3"
    assert rows[0].source == "oplab"
    assert rows[0].close == 49.46
    assert rows[0].volume == 8926600
    assert rows[0].quality_flags == ("availability_is_ingestion_time",)
    assert rows[1].close == 49.61


def test_oplab_historical_rejects_identity_mismatch():
    payload = {"symbol": "VALE3", "resolution": "1d", "data": []}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(payload).encode()

    with patch.dict("os.environ", {"OPLAB_API_TOKEN": "secret-token"}), patch(
        "b3_agent.providers.oplab.historical.urllib.request.urlopen",
        return_value=Response(),
    ):
        try:
            OplabHistoricalAdapter().get_market_data(
                "WEGE3",
                date(2026, 9, 1),
                date(2026, 10, 1),
            )
        except ValueError as exc:
            assert "identity mismatch" in str(exc)
        else:
            raise AssertionError("identity mismatch must be rejected")


def test_oplab_historical_requires_token():
    with patch.dict("os.environ", {}, clear=True):
        try:
            OplabHistoricalAdapter().get_market_data(
                "WEGE3",
                date(2026, 9, 1),
                date(2026, 10, 1),
            )
        except RuntimeError as exc:
            assert "OPLAB_API_TOKEN" in str(exc)
        else:
            raise AssertionError("missing token must be rejected")
