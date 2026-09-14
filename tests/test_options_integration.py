from datetime import date

from b3_agent.options import (
    CallAnalysisEngine,
    OptionsAnalysisEngine,
    OptionsPolicy,
    PutAnalysisEngine,
)


def test_put_and_call_share_one_options_analysis_contract():
    as_of = date(2026, 9, 14)
    put = PutAnalysisEngine().analyze(
        option_id="PUT1",
        underlying_ticker="ITUB4",
        strike=40.0,
        expiration_date=date(2026, 10, 16),
        premium=1.50,
        contract_multiplier=100.0,
        as_of=as_of,
        fair_value=45.0,
    )
    call = CallAnalysisEngine().analyze(
        option_id="CALL1",
        underlying_ticker="ITUB4",
        strike=43.0,
        expiration_date=date(2026, 10, 16),
        premium=1.0,
        contract_multiplier=100.0,
        as_of=as_of,
        current_price=40.0,
        fair_value=45.0,
    )

    result = OptionsAnalysisEngine().combine(
        puts=(put,),
        calls=(call,),
        source_refs=("oplab:ITUB4:2026-09-14",),
    )

    assert len(result.puts) == 1
    assert len(result.calls) == 1
    assert result.opportunities == (put, call)
    assert result.quality_status == "VALIDATED"


def test_options_policy_evaluates_put_and_call_deterministically():
    policy = OptionsPolicy(
        min_put_annualized_return=0.10,
        min_put_margin_of_safety=0.10,
        min_call_annualized_premium_return=0.20,
        min_call_total_return_if_assigned=0.05,
        max_call_upside_surrendered=3.0,
    )
    put = PutAnalysisEngine().analyze(
        option_id="PUT1",
        underlying_ticker="ITUB4",
        strike=40.0,
        expiration_date=date(2026, 10, 16),
        premium=1.50,
        contract_multiplier=100.0,
        as_of=date(2026, 9, 14),
        fair_value=45.0,
    )
    call = CallAnalysisEngine().analyze(
        option_id="CALL1",
        underlying_ticker="ITUB4",
        strike=43.0,
        expiration_date=date(2026, 10, 16),
        premium=1.0,
        contract_multiplier=100.0,
        as_of=date(2026, 9, 14),
        current_price=40.0,
        fair_value=45.0,
    )

    assert policy.evaluate_put(put) == "SELL_PUT"
    assert policy.evaluate_call(call) == "SELL_CALL"


def test_put_without_fair_value_does_not_get_sell_recommendation():
    put = PutAnalysisEngine().analyze(
        option_id="PUT1",
        underlying_ticker="ITUB4",
        strike=40.0,
        expiration_date=date(2026, 10, 16),
        premium=1.50,
        contract_multiplier=100.0,
        as_of=date(2026, 9, 14),
    )
    policy = OptionsPolicy(min_put_annualized_return=0.01)
    assert policy.evaluate_put(put) == "HOLD_WAIT"
