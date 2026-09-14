from datetime import date

import pytest

from b3_agent.schemas.valuation import ValuationInputs
from b3_agent.valuation.dcf import DCFValuationEngine


def make_inputs(*, net_debt: float | None = 200.0, shares_outstanding: float | None = 50.0) -> ValuationInputs:
    return ValuationInputs(
        instrument_id="B3-TEST4",
        ticker="TEST4",
        as_of=date(2026, 9, 14),
        method="DCF",
        net_debt=net_debt,
        shares_outstanding=shares_outstanding,
        assumptions={"source": "test"},
        source_refs=("test:fcf",),
    )


def kwargs():
    return dict(
        fcf_bear=(80.0, 85.0, 90.0),
        fcf_base=(100.0, 110.0, 121.0),
        fcf_bull=(120.0, 135.0, 151.875),
        discount_rate_bear=0.12,
        discount_rate_base=0.10,
        discount_rate_bull=0.09,
        terminal_growth_bear=0.02,
        terminal_growth_base=0.025,
        terminal_growth_bull=0.03,
    )


def test_dcf_calculates_equity_value_per_share():
    result = DCFValuationEngine().value_non_financial(make_inputs(), **kwargs())
    assert result.method == "DCF"
    assert result.bear_value < result.base_value < result.bull_value


def test_dcf_preserves_audit_fields():
    result = DCFValuationEngine().value_non_financial(make_inputs(), **kwargs())
    assert result.instrument_id == "B3-TEST4"
    assert result.ticker == "TEST4"
    assert result.as_of == date(2026, 9, 14)
    assert result.assumptions["source"] == "test"
    assert result.assumptions["net_debt"] == 200.0
    assert result.assumptions["shares_outstanding"] == 50.0
    assert result.source_refs == ("test:fcf",)


@pytest.mark.parametrize("field", ["net_debt", "shares_outstanding"])
def test_dcf_requires_inputs(field):
    with pytest.raises(ValueError, match=f"{field} is required"):
        DCFValuationEngine().value_non_financial(make_inputs(**{field: None}), **kwargs())


def test_dcf_rejects_empty_forecast():
    values = kwargs()
    values["fcf_base"] = ()
    with pytest.raises(ValueError, match="forecast cannot be empty"):
        DCFValuationEngine().value_non_financial(make_inputs(), **values)


def test_dcf_rejects_mismatched_horizon():
    values = kwargs()
    values["fcf_bull"] = (120.0, 135.0)
    with pytest.raises(ValueError, match="same forecast horizon"):
        DCFValuationEngine().value_non_financial(make_inputs(), **values)


def test_dcf_rejects_discount_rate_not_above_terminal_growth():
    values = kwargs()
    values["discount_rate_base"] = 0.02
    with pytest.raises(ValueError, match="discount_rate_base must be greater"):
        DCFValuationEngine().value_non_financial(make_inputs(), **values)


def test_dcf_rejects_non_positive_discount_rate():
    values = kwargs()
    values["discount_rate_bear"] = 0.0
    with pytest.raises(ValueError, match="discount rates must be positive"):
        DCFValuationEngine().value_non_financial(make_inputs(), **values)


def test_dcf_rejects_negative_terminal_growth():
    values = kwargs()
    values["terminal_growth_base"] = -0.01
    with pytest.raises(ValueError, match="terminal growth rates cannot be negative"):
        DCFValuationEngine().value_non_financial(make_inputs(), **values)
