from datetime import date

import pytest

from b3_agent.options import PutAnalysisEngine


AS_OF = date(2026, 9, 14)


def test_put_effective_price_and_annualized_return():
    result = PutAnalysisEngine().analyze(
        option_id="ITUBV403",
        underlying_ticker="ITUB4",
        strike=40.0,
        expiration_date=date(2026, 10, 16),
        premium=1.50,
        contract_multiplier=100.0,
        as_of=AS_OF,
        fair_value=45.0,
    )
    assert result.effective_price == pytest.approx(38.50)
    assert result.annualized_return == pytest.approx((1.50 / 38.50) * (365 / 32))
    assert result.margin_of_safety == pytest.approx((45.0 - 38.5) / 45.0)
    assert result.days_to_expiration == 32


def test_put_preserves_configured_multiplier():
    result = PutAnalysisEngine().analyze(
        option_id="ABCV100",
        underlying_ticker="ABC3",
        strike=100.0,
        expiration_date=date(2026, 10, 14),
        premium=2.0,
        contract_multiplier=75.0,
        as_of=AS_OF,
    )
    assert result.contract_multiplier == 75.0


def test_put_rejects_expired_option():
    with pytest.raises(ValueError, match="expiration_date"):
        PutAnalysisEngine().analyze(
            option_id="ABCV100",
            underlying_ticker="ABC3",
            strike=100.0,
            expiration_date=AS_OF,
            premium=2.0,
            contract_multiplier=100.0,
            as_of=AS_OF,
        )


def test_put_rejects_non_positive_effective_price():
    with pytest.raises(ValueError, match="effective price"):
        PutAnalysisEngine().analyze(
            option_id="ABCV100",
            underlying_ticker="ABC3",
            strike=100.0,
            expiration_date=date(2026, 10, 14),
            premium=100.0,
            contract_multiplier=100.0,
            as_of=AS_OF,
        )
