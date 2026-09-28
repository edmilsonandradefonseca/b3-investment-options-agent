from __future__ import annotations

from datetime import date

import pytest

import b3_agent.orchestration.fast_dispatch as fast_dispatch
from b3_agent.orchestration.fast_dispatch import FastRouteDispatcher
from b3_agent.schemas.position import PortfolioContext, Position


def _portfolio() -> PortfolioContext:
    return PortfolioContext(
        as_of=date(2026, 9, 27),
        cash=10000.0,
        cash_is_known=True,
        positions=(
            Position(
                position_id="PETR4-STOCK",
                ticker="PETR4",
                instrument_type="STOCK",
                quantity=100,
                market_price=40.0,
                market_value=4000.0,
                source_ref="BTG:Renda Variavel:Acoes",
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
                source_ref="BTG:Renda Variavel:Opcoes",
            ),
        ),
        source_refs=("BTG:Renda Variavel:Acoes", "BTG:Renda Variavel:Opcoes"),
    )


def _install_portfolio(monkeypatch):
    monkeypatch.setattr(
        fast_dispatch,
        "load_active_snapshots",
        lambda data_dir: {"portfolio_context": _portfolio()},
    )


def test_portfolio_dashboard_is_served_without_llm(monkeypatch):
    _install_portfolio(monkeypatch)
    response = FastRouteDispatcher().dispatch(
        task="UC-01 Portfolio Intelligence: apresente posições e concentração.",
        context={
            "dashboard_page": "Portfolio",
            "use_cases": ["UC-01"],
        },
    )

    assert response is not None
    assert response.status == "COMPLETED"
    assert response.result["fast_route"]["target"] == "portfolio_engine"
    assert len(response.result["portfolio_context"]["positions"]) == 2
    assert response.audit[0]["event"] == "fast_router_dispatch"


def test_options_dashboard_returns_held_options_without_live_llm(monkeypatch):
    _install_portfolio(monkeypatch)
    response = FastRouteDispatcher().dispatch(
        task="UC-02 Options Position & Lifecycle Intelligence.",
        context={
            "dashboard_page": "Options",
            "use_cases": ["UC-02"],
        },
    )

    assert response is not None
    assert response.status == "COMPLETED"
    assert response.result["fast_route"]["target"] == "options_engine"
    assert response.result["option_position_count"] == 1
    assert response.result["option_positions"][0]["ticker"] == "PETRV350"
    assert response.result["option_positions"][0]["dte"] == 33
    assert "live_option_metrics" not in response.result


def test_risk_dashboard_without_explicit_shock_is_limited_not_llm(monkeypatch):
    _install_portfolio(monkeypatch)
    response = FastRouteDispatcher().dispatch(
        task="UC-11 Risk, Scenario & Stress Intelligence.",
        context={
            "dashboard_page": "Risk & Stress",
            "use_cases": ["UC-11"],
        },
    )

    assert response is not None
    assert response.status == "LIMITED"
    assert response.result["fast_route"]["target"] == "stress_engine"
    assert response.result["scenario_result"] is None
    assert response.result["quality_status"] == "LIMITED"


def test_explicit_ticker_stress_runs_deterministically(monkeypatch):
    _install_portfolio(monkeypatch)
    response = FastRouteDispatcher().dispatch(
        task="rode stress PETR4 -10%",
    )

    assert response is not None
    assert response.status == "COMPLETED"
    result = response.result["scenario_result"]
    assert result["sensitivities"]["ticker:PETR4"] == pytest.approx(-0.10)
    assert result["portfolio_pnl"] == pytest.approx(-380.0)


def test_complex_question_escalates_instead_of_using_dashboard_metadata(monkeypatch):
    _install_portfolio(monkeypatch)
    response = FastRouteDispatcher().dispatch(
        task="vale a pena vender PETR4 agora?",
        context={
            "dashboard_page": "Portfolio",
            "use_cases": ["UC-01"],
        },
    )

    assert response is None
