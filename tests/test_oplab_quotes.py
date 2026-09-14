from datetime import datetime
from unittest.mock import patch

from b3_agent.providers.oplab.quotes import OplabOptionQuoteAdapter


def test_oplab_get_option_quotes_maps_market_data():
    payload = [
        {
            "symbol": "ITUBI184",
            "bid": 20.00,
            "ask": 20.20,
            "close": 20.10,
            "volume": 1500,
            "time": 1789162800000,
        },
        {
            "symbol": "ITUBU184",
            "bid": 0.80,
            "ask": 0.90,
            "close": 0.85,
            "volume": 2500,
            "time": 1789162800000,
        },
    ]

    adapter = OplabOptionQuoteAdapter()

    with patch.dict("os.environ", {"OPLAB_API_TOKEN": "test-token"}), patch(
        "b3_agent.providers.oplab.quotes.urllib.request.urlopen"
    ) as mock_urlopen:
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = __import__("json").dumps(payload).encode()

        records = adapter.get_option_quotes(
            "ITUB4",
            datetime(2026, 9, 13),
        )

    assert len(records) == 2

    call = records[0]

    assert call.instrument_id == "ITUBI184"
    assert call.ticker == "ITUBI184"
    assert call.option_id == "ITUBI184"
    assert call.bid == 20.00
    assert call.ask == 20.20
    assert call.last == 20.10
    assert call.mid == 20.10
    assert call.volume == 1500
    assert call.open_interest is None
    assert call.implied_volatility is None
    assert call.delta is None
    assert call.gamma is None
    assert call.theta is None
    assert call.vega is None
    assert call.rho is None
    assert call.source == "oplab"


def test_oplab_option_quotes_rejects_empty_ticker():
    adapter = OplabOptionQuoteAdapter()

    try:
        adapter.get_option_quotes(
            "",
            datetime(2026, 9, 13),
        )
    except ValueError as exc:
        assert str(exc) == "ticker must not be empty"
    else:
        raise AssertionError("Expected ValueError")


def test_oplab_option_quotes_treat_zero_market_values_as_unavailable():
    payload = [
        {
            "symbol": "ITUBU184",
            "bid": 0,
            "ask": 0,
            "close": 0,
            "volume": 0,
            "time": 1789162800000,
        }
    ]

    adapter = OplabOptionQuoteAdapter()

    with patch.dict("os.environ", {"OPLAB_API_TOKEN": "test-token"}), patch(
        "b3_agent.providers.oplab.quotes.urllib.request.urlopen"
    ) as mock_urlopen:
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = __import__("json").dumps(payload).encode()

        records = adapter.get_option_quotes(
            "ITUB4",
            datetime(2026, 9, 13),
        )

    record = records[0]

    assert record.bid is None
    assert record.ask is None
    assert record.mid is None
    assert record.last is None
    assert record.volume == 0
