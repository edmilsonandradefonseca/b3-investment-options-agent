from datetime import date

import pytest

from b3_agent.scenario import ScenarioStressEngine
from b3_agent.schemas.position import PortfolioContext, Position
from b3_agent.schemas.scenario import ScenarioDefinition
from b3_agent.schemas.strategy_comparison import StrategyAlternative
from b3_agent.strategy_comparison import StrategyComparisonEngine


def portfolio():
    return PortfolioContext(
        as_of=date(2026, 9, 26),
        cash=10000.0,
        positions=(
            Position(
                position_id="PETR4-STOCK",
                ticker="PETR4",
                instrument_type="STOCK",
                quantity=100,
                market_price=40.0,
                market_value=4000.0,
            ),
            Position(
                position_id="PETR4-PUT",
                ticker="PETRV350",
                instrument_type="OPTION",
                quantity=-1,
                strike=35.0,
                expiration_date=date(2026, 10, 30),
                option_type="PUT",
                underlying_ticker="PETR4",
                contract_multiplier=100,
                market_price=2.0,
                market_value=-200.0,
            ),
        ),
        source_refs=("portfolio:test",),
    )


def test_scenario_stress_applies_explicit_ticker_and_position_shocks():
    scenario = ScenarioDefinition(
        scenario_id="SCN-1",
        name="PETR4 down 20%",
        as_of=date(2026, 9, 26),
        ticker_price_shocks={"PETR4": -0.20},
        position_value_shocks={"PETR4-PUT": 0.50},
        source_refs=("scenario:test",),
    )

    result = ScenarioStressEngine().evaluate(portfolio(), scenario)

    by_id = {item.position_id: item for item in result.position_stress}
    assert by_id["PETR4-STOCK"].stressed_value == pytest.approx(3200.0)
    assert by_id["PETR4-PUT"].stressed_value == pytest.approx(-300.0)
    assert result.base_portfolio_value == pytest.approx(13800.0)
    assert result.stressed_portfolio_value == pytest.approx(12900.0)
    assert result.portfolio_pnl == pytest.approx(-900.0)
    assert result.assignment_capital == pytest.approx(3500.0)
    assert result.cash_after_assignment == pytest.approx(6500.0)
    assert result.quality_status == "VALIDATED"


def test_scenario_marks_warning_when_market_value_missing():
    p = PortfolioContext(
        as_of=date(2026, 9, 26),
        cash=1000.0,
        positions=(
            Position(
                position_id="VALE3",
                ticker="VALE3",
                instrument_type="STOCK",
                quantity=10,
                market_value=None,
            ),
        ),
    )
    result = ScenarioStressEngine().evaluate(
        p,
        ScenarioDefinition(
            scenario_id="SCN-MISSING",
            name="missing value",
            as_of=date(2026, 9, 26),
            ticker_price_shocks={"VALE3": -0.1},
        ),
    )
    assert result.quality_status == "WARNING"


def test_scenario_rejects_loss_beyond_100_percent():
    with pytest.raises(ValueError, match="greater than -100%"):
        ScenarioDefinition(
            scenario_id="BAD",
            name="bad",
            as_of=date(2026, 9, 26),
            ticker_price_shocks={"PETR4": -1.0},
        )


def alternative(
    alternative_id: str,
    *,
    capital: float,
    expected_return: float,
    max_loss: float,
    liquidity: float,
    portfolio_impact: float,
    historical_similarity: float,
    experience_confidence: float,
    base_payoff: float,
):
    return StrategyAlternative(
        alternative_id=alternative_id,
        label=alternative_id,
        action_type=alternative_id,
        subject_id="B3-PETR4",
        as_of=date(2026, 9, 26),
        capital_required=capital,
        expected_return=expected_return,
        max_loss=max_loss,
        liquidity_score=liquidity,
        portfolio_impact=portfolio_impact,
        historical_similarity=historical_similarity,
        experience_confidence=experience_confidence,
        payoff_by_scenario={
            "BASE": base_payoff,
            "DOWN_15": base_payoff - 1000.0,
        },
        evidence_refs=(f"EV-{alternative_id}",),
        source_refs=("test:source",),
    )


def test_strategy_comparison_keeps_experience_separate_and_auditable():
    buy = alternative(
        "BUY_STOCK",
        capital=4000,
        expected_return=0.10,
        max_loss=-4000,
        liquidity=0.95,
        portfolio_impact=0.20,
        historical_similarity=0.55,
        experience_confidence=0.60,
        base_payoff=500,
    )
    sell_put = alternative(
        "SELL_PUT",
        capital=3500,
        expected_return=0.08,
        max_loss=-3300,
        liquidity=0.80,
        portfolio_impact=0.15,
        historical_similarity=0.82,
        experience_confidence=0.72,
        base_payoff=250,
    )

    result = StrategyComparisonEngine().compare(buy, sell_put)

    assert result.capital_delta == pytest.approx(-500)
    assert result.expected_return_delta == pytest.approx(-0.02)
    assert result.max_loss_delta == pytest.approx(700)
    assert result.historical_similarity_delta == pytest.approx(0.27)
    assert result.experience_confidence_delta == pytest.approx(0.12)
    assert result.scenario_deltas["BASE"] == pytest.approx(-250)
    assert result.assumptions["ranking"] == "not_applied"
    assert result.assumptions["experience"] == "kept_separate_from_deterministic_metrics"


def test_strategy_comparison_requires_same_as_of():
    left = StrategyAlternative(
        alternative_id="A",
        label="A",
        action_type="BUY",
        subject_id="B3-PETR4",
        as_of=date(2026, 9, 26),
    )
    right = StrategyAlternative(
        alternative_id="B",
        label="B",
        action_type="SELL_PUT",
        subject_id="B3-PETR4",
        as_of=date(2026, 9, 27),
    )
    with pytest.raises(ValueError, match="same as_of"):
        StrategyComparisonEngine().compare(left, right)
