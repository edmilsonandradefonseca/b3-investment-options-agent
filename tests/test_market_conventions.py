from b3_agent.options.market_conventions import infer_b3_option_type


def test_b3_call_series():
    assert infer_b3_option_type("PETRK376") == "CALL"


def test_b3_put_series():
    assert infer_b3_option_type("EQTLV369") == "PUT"


def test_unknown_series_returns_none():
    assert infer_b3_option_type("PETR4") is None
