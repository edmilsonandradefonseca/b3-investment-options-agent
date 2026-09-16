from datetime import datetime
from unittest.mock import patch

from b3_agent.providers.oplab.options import OplabOptionsAdapter


def test_oplab_get_options_maps_option_chain():
    payload = [{"symbol":"ITUBI184","type":"CALL","strike":18.41,"due_date":"2026-09-18","maturity_type":"American","contract_size":100},{"symbol":"ITUBU184","type":"PUT","strike":18.41,"due_date":"2026-09-18","maturity_type":"European","contract_size":100}]
    adapter = OplabOptionsAdapter()
    with patch.dict("os.environ", {"OPLAB_API_TOKEN":"test-token"}), patch("b3_agent.providers.oplab.options.urllib.request.urlopen") as mock_urlopen:
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = __import__("json").dumps(payload).encode()
        records = adapter.get_options("itub4", datetime(2026,9,13))
    assert len(records) == 2
    call = records[0]
    assert call.option_id == "ITUBI184"
    assert call.underlying_ticker == "ITUB4"
    assert call.option_ticker == "ITUBI184"
    assert call.option_type == "CALL"
    assert call.strike == 18.41
    assert call.expiration_date.isoformat() == "2026-09-18"
    assert call.exercise_style == "American"
    assert call.contract_multiplier == 100
    assert call.currency == "BRL"
    put = records[1]
    assert put.option_id == "ITUBU184"
    assert put.option_type == "PUT"
    assert put.exercise_style == "European"


def test_oplab_get_option_quotes_maps_market_fields():
    payload = [{"symbol":"ITUBI184","type":"CALL","strike":18.41,"due_date":"2026-09-18","last":0.55,"mid":0.54,"bid":0.53,"ask":0.55,"volume":1200,"open_interest":3400,"iv":0.31,"delta":0.58}]
    observed_at = datetime(2026,9,15,15,0)
    adapter = OplabOptionsAdapter()
    with patch.dict("os.environ", {"OPLAB_API_TOKEN":"test-token"}), patch("b3_agent.providers.oplab.options.urllib.request.urlopen") as mock_urlopen:
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = __import__("json").dumps(payload).encode()
        quotes = adapter.get_option_quotes("itub4", observed_at)
    assert len(quotes) == 1
    quote = quotes[0]
    assert quote.option_id == "ITUBI184"
    assert quote.source == "oplab"
    assert quote.observation_timestamp == observed_at
    assert quote.last == 0.55
    assert quote.mid == 0.54
    assert quote.bid == 0.53
    assert quote.ask == 0.55
    assert quote.volume == 1200
    assert quote.open_interest == 3400
    assert quote.implied_volatility == 0.31
    assert quote.delta == 0.58


def test_oplab_options_rejects_empty_ticker():
    adapter = OplabOptionsAdapter()
    try:
        adapter.get_options("", datetime(2026,9,13))
    except ValueError as exc:
        assert str(exc) == "ticker must not be empty"
    else:
        raise AssertionError("Expected ValueError")


def test_oplab_options_rejects_unsupported_option_type():
    payload = [{"symbol":"ITUBX184","type":"FUTURE","strike":18.41,"due_date":"2026-09-18","maturity_type":"European","contract_size":100}]
    adapter = OplabOptionsAdapter()
    with patch.dict("os.environ", {"OPLAB_API_TOKEN":"test-token"}), patch("b3_agent.providers.oplab.options.urllib.request.urlopen") as mock_urlopen:
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = __import__("json").dumps(payload).encode()
        try:
            adapter.get_options("ITUB4", datetime(2026,9,13))
        except ValueError as exc:
            assert str(exc) == "oplab returned unsupported option type: FUTURE"
        else:
            raise AssertionError("Expected ValueError")
