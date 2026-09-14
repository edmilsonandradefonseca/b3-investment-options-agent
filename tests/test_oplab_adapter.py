from datetime import date, datetime, timezone
from unittest.mock import patch

from b3_agent.providers.oplab.adapter import OplabAdapter


def test_oplab_get_market_data_maps_stock_response():
    payload = {
        "symbol": "ITUB4",
        "type": "STOCK",
        "open": 42.55,
        "high": 42.80,
        "low": 42.22,
        "close": 42.80,
        "volume": 17572900,
        "time": 1789162800000,
    }

    adapter = OplabAdapter()

    with patch.dict("os.environ", {"OPLAB_API_TOKEN": "test-token"}), patch(
        "b3_agent.providers.oplab.adapter.urllib.request.urlopen"
    ) as mock_urlopen:
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = __import__("json").dumps(payload).encode()

        records = adapter.get_market_data(
            "itub4",
            date(2026, 9, 1),
            date(2026, 9, 12),
        )

    assert len(records) == 1

    record = records[0]

    assert record.instrument_id == "ITUB4"
    assert record.ticker == "ITUB4"
    assert record.source == "oplab"
    assert record.open == 42.55
    assert record.high == 42.80
    assert record.low == 42.22
    assert record.close == 42.80
    assert record.volume == 17572900
    assert record.currency == "BRL"
    assert record.observation_timestamp == datetime.fromtimestamp(
        1789162800000 / 1000,
        tz=timezone.utc,
    )


def test_oplab_rejects_empty_ticker():
    adapter = OplabAdapter()

    try:
        adapter.get_market_data(
            "",
            date(2026, 9, 1),
            date(2026, 9, 12),
        )
    except ValueError as exc:
        assert str(exc) == "ticker must not be empty"
    else:
        raise AssertionError("Expected ValueError")


def test_oplab_rejects_invalid_date_range():
    adapter = OplabAdapter()

    try:
        adapter.get_market_data(
            "ITUB4",
            date(2026, 9, 12),
            date(2026, 9, 1),
        )
    except ValueError as exc:
        assert str(exc) == "start date must be on or before end date"
    else:
        raise AssertionError("Expected ValueError")
