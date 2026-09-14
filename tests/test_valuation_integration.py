from datetime import date

import pytest

from b3_agent.schemas.valuation import ValuationInputs
from b3_agent.valuation import (
    BankValuationEngine,
    DCFValuationEngine,
    InvestmentPricePolicy,
    MultiplesValuationEngine,
)


AS_OF = date(2026, 9, 14)


def test_pe_then_policy_preserves_valuation_and_adds_thresholds():
    inputs = ValuationInputs(
        instrument_id="ABC3", ticker="ABC3", as_of=AS_OF, method="PE",
        earnings_per_share=2.0, source_refs=("fundamentals:abc3",),
    )
    valuation = MultiplesValuationEngine().value_non_financial(
        inputs, pe_bear=8.0, pe_base=10.0, pe_bull=12.0
    )
    result = InvestmentPricePolicy().apply(valuation, margin_of_safety=0.20, current_price=16.0)
    assert (valuation.bear_value, valuation.base_value, valuation.bull_value) == (16.0, 20.0, 24.0)
    assert (result.accumulation_price, result.reduce_price, result.sell_price) == (16.0, 20.0, 24.0)
    assert result.margin_of_safety == pytest.approx(0.20)
    assert result.method == "PE"


def test_ev_ebitda_then_policy_preserves_equity_value():
    inputs = ValuationInputs(
        instrument_id="ABC3", ticker="ABC3", as_of=AS_OF, method="EV_EBITDA",
        ebitda=100.0, net_debt=200.0, shares_outstanding=100.0,
    )
    valuation = MultiplesValuationEngine().value_non_financial_ev_ebitda(
        inputs, ev_ebitda_bear=6.0, ev_ebitda_base=8.0, ev_ebitda_bull=10.0
    )
    result = InvestmentPricePolicy().apply(valuation, margin_of_safety=0.25)
    assert (valuation.bear_value, valuation.base_value, valuation.bull_value) == (4.0, 6.0, 8.0)
    assert result.accumulation_price == pytest.approx(4.5)
    assert result.reduce_price == pytest.approx(6.0)
    assert result.sell_price == pytest.approx(8.0)


def test_dcf_then_policy_keeps_scenario_ordering():
    inputs = ValuationInputs(
        instrument_id="ABC3", ticker="ABC3", as_of=AS_OF, method="DCF",
        net_debt=0.0, shares_outstanding=10.0,
    )
    valuation = DCFValuationEngine().value_non_financial(
        inputs,
        fcf_bear=(8.0, 8.0), fcf_base=(12.0, 12.0), fcf_bull=(16.0, 16.0),
        discount_rate_bear=0.12, discount_rate_base=0.10, discount_rate_bull=0.09,
        terminal_growth_bear=0.02, terminal_growth_base=0.025, terminal_growth_bull=0.03,
    )
    result = InvestmentPricePolicy().apply(valuation, margin_of_safety=0.20)
    assert valuation.bear_value <= valuation.base_value <= valuation.bull_value
    assert result.accumulation_price < result.reduce_price < result.sell_price


def test_pb_roe_then_policy_keeps_bank_audit_inputs():
    inputs = ValuationInputs(
        instrument_id="BANK3", ticker="BANK3", as_of=AS_OF, method="PB_ROE",
        book_value_per_share=20.0, source_refs=("fundamentals:bank3",),
    )
    valuation = BankValuationEngine().value_pb_roe(
        inputs,
        roe_bear=0.12, roe_base=0.15, roe_bull=0.18,
        cost_of_equity_bear=0.14, cost_of_equity_base=0.13, cost_of_equity_bull=0.12,
        growth_bear=0.04, growth_base=0.05, growth_bull=0.06,
    )
    result = InvestmentPricePolicy().apply(valuation, margin_of_safety=0.20)
    assert valuation.method == "PB_ROE"
    assert result.assumptions["roe_base"] == pytest.approx(0.15)
    assert result.source_refs == ("fundamentals:bank3",)
    assert result.accumulation_price < result.reduce_price < result.sell_price
