from datetime import date

import pytest

from b3_agent.schemas.valuation import ValuationInputs
from b3_agent.valuation import MultiplesValuationEngine


def make_inputs(*, eps: float | None = 2.0) -> ValuationInputs:
    return ValuationInputs(
        instrument_id="B3-TEST4",
        ticker="TEST4",
        as_of=date(2026, 9, 14),
        method="PE",
        earnings_per_share=eps,
        assumptions={"source": "test"},
        source_refs=("test:eps",),
    )


def test_pe_engine_calculates_bear_base_bull():
    result = MultiplesValuationEngine().value_non_financial(
        make_inputs(eps=2.0),
        pe_bear=8.0,
        pe_base=10.0,
        pe_bull=12.0,
    )

    assert result.method == "PE"
    assert result.bear_value == pytest.approx(16.0)
    assert result.base_value == pytest.approx(20.0)
    assert result.bull_value == pytest.approx(24.0)


def test_pe_engine_preserves_identity_and_audit_fields():
    result = MultiplesValuationEngine().value_non_financial(
        make_inputs(eps=3.5),
        pe_bear=7.0,
        pe_base=9.0,
        pe_bull=11.0,
    )

    assert result.instrument_id == "B3-TEST4"
    assert result.ticker == "TEST4"
    assert result.as_of == date(2026, 9, 14)
    assert result.assumptions["source"] == "test"
    assert result.assumptions["pe_bear"] == 7.0
    assert result.assumptions["pe_base"] == 9.0
    assert result.assumptions["pe_bull"] == 11.0
    assert result.source_refs == ("test:eps",)
    assert result.quality_status == "VALIDATED"


def test_pe_engine_requires_eps():
    with pytest.raises(ValueError, match="earnings_per_share is required"):
        MultiplesValuationEngine().value_non_financial(
            make_inputs(eps=None),
            pe_bear=8.0,
            pe_base=10.0,
            pe_bull=12.0,
        )


@pytest.mark.parametrize(
    "multiples",
    [
        (-1.0, 10.0, 12.0),
        (8.0, -1.0, 12.0),
        (8.0, 10.0, -1.0),
    ],
)
def test_pe_engine_rejects_negative_multiples(multiples):
    with pytest.raises(ValueError, match="cannot be negative"):
        MultiplesValuationEngine().value_non_financial(
            make_inputs(),
            pe_bear=multiples[0],
            pe_base=multiples[1],
            pe_bull=multiples[2],
        )


@pytest.mark.parametrize(
    "multiples",
    [
        (10.0, 8.0, 12.0),
        (8.0, 12.0, 10.0),
        (12.0, 10.0, 8.0),
    ],
)
def test_pe_engine_rejects_invalid_scenario_order(multiples):
    with pytest.raises(ValueError, match="bear <= base <= bull"):
        MultiplesValuationEngine().value_non_financial(
            make_inputs(),
            pe_bear=multiples[0],
            pe_base=multiples[1],
            pe_bull=multiples[2],
        )


def test_pe_engine_does_not_mix_ev_ebitda_into_equity_value():
    with pytest.raises(NotImplementedError, match="EV/EBITDA requires"):
        MultiplesValuationEngine().value_non_financial(
            make_inputs(),
            pe_bear=8.0,
            pe_base=10.0,
            pe_bull=12.0,
            ev_ebitda_base=7.0,
        )
