from b3_agent.quant_engine import _macd, _rsi


def test_rsi_uptrend():
    prices = list(range(1, 21))
    result = _rsi(prices, 14)

    assert result == 100.0


def test_rsi_downtrend():
    prices = list(range(20, 0, -1))
    result = _rsi(prices, 14)

    assert result == 0.0


def test_rsi_requires_enough_data():
    prices = list(range(1, 14))

    assert _rsi(prices, 14) is None


def test_macd_requires_enough_data():
    prices = list(range(1, 26))

    macd, signal, histogram = _macd(prices)

    assert macd is None
    assert signal is None
    assert histogram is None


def test_macd_is_deterministic():
    prices = [100 + i * 0.5 for i in range(60)]

    first = _macd(prices)
    second = _macd(prices)

    assert first == second
    assert first[0] is not None
    assert first[1] is not None
    assert first[2] is not None
