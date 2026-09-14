from datetime import date

import pytest

from b3_agent.schemas.valuation import ValuationInputs
from b3_agent.valuation.bank import BankValuationEngine


def make_inputs() -> ValuationInputs:
    return ValuationInputs(
        instrument_id="ITUB4",
        ticker="ITUB4",
        as_of=date(2026, 9, 14),
        method="PB_ROE",
        book_value_per_share=20.0,
        source_refs=("fundamentals:itub4",),
    )


def test_bank_pb_roe_calculation():
    result = BankValuationEngine().value_bank(
        make_inputs(),
        roe_bear=0.14,
        roe_base=0.18,
        roe_bull=0.22,
        cost_of_equity_bear=0.16,
        cost_of_equity_base=0.15,
        cost_of_equity_bull=0.14,
        terminal_growth_bear=0.05,
        terminal_growth_base=0.05,
        terminal_growth_bull=0.05,
    )
    assert result.bear_value == pytest.approx(20.0)
    assert result.base_value == pytest.approx(32.5)
    assert result.bull_value == pytest.approx(40.0)
    assert result.method == "PB_ROE"


def test_bank_pb_roe_preserves_audit_fields():
    result = BankValuationEngine().value_bank(
        make_inputs(),
        roe_bear=0.14, roe_base=0.18, roe_bull=0.22,
        cost_of_equity_bear=0.16, cost_of_equity_base=0.15, cost_of_equity_bull=0.14,
        terminal_growth_bear=0.05, terminal_growth_base=0.05, terminal_growth_bull=0.05,
    )
    assert result.source_refs == ("fundamentals:itub4",)
    assert result.quality_status == "VALIDATED"
    assert result.assumptions["roe_base"] == 0.18
    assert result.assumptions["book_value_per_share"] == 20.0


def test_bank_pb_roe_requires_book_value():
    inputs = ValuationInputs("ITUB4", "ITUB4", date(2026, 9, 14), "PB_ROE")
    with pytest.raises(ValueError, match="book_value_per_share"):
        BankValuationEngine().value_bank(
            inputs,
            roe_bear=0.14, roe_base=0.18, roe_bull=0.22,
            cost_of_equity_bear=0.16, cost_of_equity_base=0.15, cost_of_equity_bull=0.14,
            terminal_growth_bear=0.05, terminal_growth_base=0.05, terminal_growth_bull=0.05,
        )


def test_bank_pb_roe_rejects_invalid_rates():
    with pytest.raises(ValueError, match="cost of equity must be greater"):
        BankValuationEngine().value_bank(
            make_inputs(),
            roe_bear=0.14, roe_base=0.18, roe_bull=0.22,
            cost_of_equity_bear=0.05, cost_of_equity_base=0.15, cost_of_equity_bull=0.14,
            terminal_growth_bear=0.05, terminal_growth_base=0.05, terminal_growth_bull=0.05,
        )


def test_bank_pb_roe_rejects_negative_roe():
    with pytest.raises(ValueError, match="ROE cannot be negative"):
        BankValuationEngine().value_bank(
            make_inputs(),
            roe_bear=-0.01, roe_base=0.18, roe_bull=0.22,
            cost_of_equity_bear=0.16, cost_of_equity_base=0.15, cost_of_equity_bull=0.14,
            terminal_growth_bear=0.05, terminal_growth_base=0.05, terminal_growth_bull=0.05,
        )
