from datetime import date

from b3_agent.opportunity_options import OptionsOpportunityProducer
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.options.call import CallOpportunity
from b3_agent.options.put import PutOpportunity


def test_maps_put_and_eligible_call_to_canonical_opportunities() -> None:
    analysis = OptionsAnalysis(
        puts=(
            PutOpportunity(
                option_id="PETR4_PUT_30",
                underlying_ticker="PETR4",
                strike=30.0,
                expiration_date=date(2026, 12, 18),
                premium=1.5,
                contract_multiplier=1.0,
                effective_price=28.5,
                annualized_return=0.42,
                days_to_expiration=90,
            ),
        ),
        calls=(
            CallOpportunity(
                option_id="PETR4_CALL_38",
                underlying_ticker="PETR4",
                strike=38.0,
                expiration_date=date(2026, 12, 18),
                premium=1.2,
                contract_multiplier=1.0,
                current_price=35.0,
                days_to_expiration=90,
                premium_return=1.2 / 35.0,
                annualized_premium_return=(1.2 / 35.0) * (365.0 / 90.0),
                gain_to_strike=3.0,
                total_return_if_assigned=(38.0 + 1.2 - 35.0) / 35.0,
                action="SELL_CALL",
            ),
        ),
        source_refs=("OPLAB",),
    )

    result = OptionsOpportunityProducer().produce(
        analysis,
        as_of=date(2026, 9, 15),
    )

    assert [item.opportunity_id for item in result] == [
        "SELL_PUT:PETR4_PUT_30",
        "SELL_CALL:PETR4_CALL_38",
    ]
    assert result[0].action == "SELL_PUT"
    assert result[0].expected_return == 0.42
    assert result[0].capital_requirement == 30.0
    assert result[0].source_refs == ("OPLAB",)
    assert result[1].action == "SELL_CALL"


def test_does_not_promote_hold_wait_call() -> None:
    analysis = OptionsAnalysis(
        calls=(
            CallOpportunity(
                option_id="PETR4_CALL_40",
                underlying_ticker="PETR4",
                strike=40.0,
                expiration_date=date(2026, 12, 18),
                premium=0.5,
                contract_multiplier=1.0,
                current_price=35.0,
                days_to_expiration=90,
                premium_return=0.5 / 35.0,
                annualized_premium_return=(0.5 / 35.0) * (365.0 / 90.0),
                gain_to_strike=5.0,
                total_return_if_assigned=(40.0 + 0.5 - 35.0) / 35.0,
                action="HOLD_WAIT",
            ),
        )
    )

    result = OptionsOpportunityProducer().produce(
        analysis,
        as_of=date(2026, 9, 15),
    )

    assert result == ()
