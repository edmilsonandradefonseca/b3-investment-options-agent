from datetime import date

import pytest

from b3_agent.options.call import CallAnalysisEngine


def test_call_returns_and_upside_are_deterministic() -> None:
    result = CallAnalysisEngine().analyze(
        option_id="CALL1",
        underlying_ticker="ITUB4",
        strike=43.0,
        expiration_date=date(2026, 10, 16),
        premium=1.0,
        contract_multiplier=100.0,
        as_of=date(2026, 9, 16),
        current_price=40.0,
        fair_value=45.0,
    )

    assert result.days_to_expiration == 30
    assert result.premium_return == pytest.approx(0.025)
    assert result.annualized_premium_return == pytest.approx(0.025 * 365 / 30)
    assert result.gain_to_strike == pytest.approx(3.0)
    assert result.total_return_if_assigned == pytest.approx(0.10)
    assert result.upside_surrendered == pytest.approx(2.0)
    assert result.action == "SELL_CALL"
    assert result.contract_multiplier == 100.0


def test_call_can_be_held_when_upside_surrender_exceeds_policy() -> None:
    result = CallAnalysisEngine().analyze(
        option_id="CALL2",
        underlying_ticker="ITUB4",
        strike=43.0,
        expiration_date=date(2026, 10, 16),
        premium=1.0,
        contract_multiplier=100.0,
        as_of=date(2026, 9, 16),
        current_price=40.0,
        fair_value=50.0,
        max_upside_surrendered=3.0,
    )

    assert result.action == "HOLD_WAIT"
    assert result.upside_surrendered == pytest.approx(7.0)


def test_call_can_be_held_when_return_threshold_is_not_met() -> None:
    result = CallAnalysisEngine().analyze(
        option_id="CALL3",
        underlying_ticker="ITUB4",
        strike=41.0,
        expiration_date=date(2026, 10, 16),
        premium=0.10,
        contract_multiplier=100.0,
        as_of=date(2026, 9, 16),
        current_price=40.0,
        min_annualized_premium_return=0.05,
    )

    assert result.action == "HOLD_WAIT"


def test_call_rejects_expired_contract() -> None:
    with pytest.raises(ValueError, match="expiration_date must be after as_of"):
        CallAnalysisEngine().analyze(
            option_id="CALL4",
            underlying_ticker="ITUB4",
            strike=41.0,
            expiration_date=date(2026, 9, 15),
            premium=1.0,
            contract_multiplier=100.0,
            as_of=date(2026, 9, 16),
            current_price=40.0,
        )


def test_call_rejects_invalid_current_price() -> None:
    with pytest.raises(ValueError, match="current_price must be positive"):
        CallAnalysisEngine().analyze(
            option_id="CALL5",
            underlying_ticker="ITUB4",
            strike=41.0,
            expiration_date=date(2026, 10, 16),
            premium=1.0,
            contract_multiplier=100.0,
            as_of=date(2026, 9, 16),
            current_price=0.0,
        )
