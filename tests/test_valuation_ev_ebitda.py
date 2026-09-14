from datetime import date

import pytest

from b3_agent.schemas.valuation import ValuationInputs
from b3_agent.valuation import MultiplesValuationEngine


def make_inputs(
    *,
    ebitda: float | None = 100.0,
    net_debt: float | None = 200.0,
    shares_outstanding: float | None = 50.0,
) -> ValuationInputs:
    return ValuationInputs(
        instrument_id="B3-TEST4",
        ticker="TEST4",
        as_of=date(2026, 9, 14),
        method="EV_EBITDA",
        ebitda=ebitda,
        net_debt=net_debt,
        shares_outstanding=shares_outstanding,
        assumptions={"source": "test"},
        source_refs=("test:ev-ebitda",),
    )


def test_ev_ebitda_converts_enterprise_value_to_equity_value_per_share():
    result = MultiplesValuationEngine().value_non_financial_ev_ebitda(
        make_inputs(),
        ev_ebitda_bear=6.0,
        ev_ebitda_base=8.0,
        ev_ebitda_bull=10.0,
    )

    assert result.method == "EV_EBITDA"
    assert result.bear_value == pytest.approx(8.0)
    assert result.base_value == pytest.approx(12.0)
    assert result.bull_value == pytest.approx(16.0)


def test_ev_ebitda_preserves_audit_fields():
    result = MultiplesValuationEngine().value_non_financial_ev_ebitda(
        make_inputs(),
        ev_ebitda_bear=6.0,
        ev_ebitda_base=8.0,
        ev_ebitda_bull=10.0,
    )

    assert result.instrument_id == "B3-TEST4"
    assert result.ticker == "TEST4"
    assert result.as_of == date(2026, 9, 14)
    assert result.assumptions["source"] == "test"
    assert result.assumptions["net_debt"] == 200.0
    assert result.assumptions["shares_outstanding"] == 50.0
    assert result.assumptions["ev_ebitda_base"] == 8.0
    assert result.source_refs == ("test:ev-ebitda",)


@pytest.mark.parametrize("field", ["ebitda", "net_debt", "shares_outstanding"])
def test_ev_ebitda_requires_inputs(field):
    kwargs = {field: None}
    with pytest.raises(ValueError, match=f"{field} is required"):
        MultiplesValuationEngine().value_non_financial_ev_ebitda(
            make_inputs(**kwargs),
            ev_ebitda_bear=6.0,
            ev_ebitda_base=8.0,
            ev_ebitda_bull=10.0,
        )


def test_ev_ebitda_rejects_non_positive_ebitda():
    with pytest.raises(ValueError, match="ebitda must be positive"):
        MultiplesValuationEngine().value_non_financial_ev_ebitda(
            make_inputs(ebitda=0.0),
            ev_ebitda_bear=6.0,
            ev_ebitda_base=8.0,
            ev_ebitda_bull=10.0,
        )


def test_ev_ebitda_rejects_non_positive_share_count():
    with pytest.raises(ValueError, match="shares_outstanding must be positive"):
        MultiplesValuationEngine().value_non_financial_ev_ebitda(
            make_inputs(shares_outstanding=0.0),
            ev_ebitda_bear=6.0,
            ev_ebitda_base=8.0,
            ev_ebitda_bull=10.0,
        )


@pytest.mark.parametrize(
    "multiples",
    [
        (-1.0, 8.0, 10.0),
        (6.0, -1.0, 10.0),
        (6.0, 8.0, -1.0),
    ],
)
def test_ev_ebitda_rejects_negative_multiples(multiples):
    with pytest.raises(ValueError, match="cannot be negative"):
        MultiplesValuationEngine().value_non_financial_ev_ebitda(
            make_inputs(),
            ev_ebitda_bear=multiples[0],
            ev_ebitda_base=multiples[1],
            ev_ebitda_bull=multiples[2],
        )


@pytest.mark.parametrize(
    "multiples",
    [(8.0, 6.0, 10.0), (6.0, 10.0, 8.0), (10.0, 8.0, 6.0)],
)
def test_ev_ebitda_rejects_invalid_scenario_order(multiples):
    with pytest.raises(ValueError, match="bear <= base <= bull"):
        MultiplesValuationEngine().value_non_financial_ev_ebitda(
            make_inputs(),
            ev_ebitda_bear=multiples[0],
            ev_ebitda_base=multiples[1],
            ev_ebitda_bull=multiples[2],
        )
