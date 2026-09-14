from datetime import date

import pytest

from b3_agent.schemas.valuation import ValuationRange
from b3_agent.valuation.policy import InvestmentPricePolicy


def make_valuation() -> ValuationRange:
    return ValuationRange(
        instrument_id="ITUB4",
        ticker="ITUB4",
        as_of=date(2026, 9, 14),
        method="PB_ROE",
        bear_value=20.0,
        base_value=30.0,
        bull_value=40.0,
        assumptions={"roe_base": 0.18},
        source_refs=("fundamentals:itub4",),
    )


def test_policy_builds_price_thresholds_from_explicit_margin():
    result = InvestmentPricePolicy().apply(make_valuation(), margin_of_safety=0.20)

    assert result.accumulation_price == pytest.approx(24.0)
    assert result.reduce_price == pytest.approx(30.0)
    assert result.sell_price == pytest.approx(40.0)
    assert result.margin_of_safety is None


def test_policy_calculates_current_margin_of_safety():
    result = InvestmentPricePolicy().apply(
        make_valuation(), margin_of_safety=0.20, current_price=24.0
    )
    assert result.margin_of_safety == pytest.approx(0.20)
    assert result.assumptions["current_price"] == 24.0


def test_policy_preserves_valuation_and_audit_fields():
    result = InvestmentPricePolicy().apply(make_valuation(), margin_of_safety=0.20)
    assert (result.bear_value, result.base_value, result.bull_value) == (20.0, 30.0, 40.0)
    assert result.source_refs == ("fundamentals:itub4",)
    assert result.assumptions["roe_base"] == 0.18
    assert result.assumptions["policy_margin_of_safety"] == 0.20


@pytest.mark.parametrize("margin", [-0.01, 1.0, 1.5])
def test_policy_rejects_invalid_margin(margin: float):
    with pytest.raises(ValueError, match="margin_of_safety"):
        InvestmentPricePolicy().apply(make_valuation(), margin_of_safety=margin)


def test_policy_rejects_negative_current_price():
    with pytest.raises(ValueError, match="current_price"):
        InvestmentPricePolicy().apply(
            make_valuation(), margin_of_safety=0.20, current_price=-1.0
        )
