from __future__ import annotations

from datetime import date

import pytest

import b3_agent.orchestration.fast_dispatch as fast_dispatch
from b3_agent.orchestration.fast_dispatch import FastRouteDispatcher
from b3_agent.schemas.market import StockMarketData
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
                average_cost=35.0,
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
                average_cost=2.5,
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
    pnl = {item["position_id"]: item for item in response.result["position_pnl"]}
    assert pnl["PETR4-STOCK"]["unrealized_pnl"] == pytest.approx(500.0)
    assert pnl["PETR4-PUT"]["unrealized_pnl"] == pytest.approx(50.0)
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


def test_structured_strategy_comparison_dispatches_without_llm(monkeypatch):
    _install_portfolio(monkeypatch)

    class FakeStrategyService:
        def compare(self, **kwargs):
            assert kwargs["assets"] == ("VALE3", "WEGE3")
            assert kwargs["strategies"] == ("Comprar ação", "Comprar ação")
            assert kwargs["option_ids"] == (None, None)
            assert kwargs["amount"] == 50000.0
            return {
                "as_of": "2026-10-01T15:00:00+00:00",
                "quality_status": "VALIDATED",
                "summary": "comparison ready",
                "strategy_comparison": {"assumptions": {"ranking": "not_applied"}},
                "asset_evidence": {"VALE3": {}, "WEGE3": {}},
                "limitations": [],
                "source_refs": ["brapi"],
            }

    monkeypatch.setattr(fast_dispatch, "LiveStrategyComparisonService", FakeStrategyService)
    response = FastRouteDispatcher().dispatch(
        task="UC-04: compare Comprar ação em VALE3 e Comprar ação em WEGE3",
        context={
            "workspace": "Strategy Lab",
            "comparison_assets": ["VALE3", "WEGE3"],
            "strategy_a": "Comprar ação",
            "strategy_b": "Comprar ação",
            "comparison_amount": 50000,
        },
    )

    assert response is not None
    assert response.status == "COMPLETED"
    assert response.result["fast_route"]["target"] == "strategy_engine"
    assert set(response.result["asset_evidence"]) == {"VALE3", "WEGE3"}
    assert response.sources == ("brapi",)


def test_structured_sell_put_dispatches_explicit_contract_without_llm(monkeypatch):
    _install_portfolio(monkeypatch)

    class FakeStrategyService:
        def compare(self, **kwargs):
            assert kwargs["assets"] == ("VALE3", "WEGE3")
            assert kwargs["strategies"] == ("Comprar ação", "Vender PUT")
            assert kwargs["option_ids"] == (None, "WEGEV500")
            return {
                "as_of": "2026-10-01T15:00:00+00:00",
                "quality_status": "WARNING",
                "summary": "comparison ready",
                "strategy_comparison": {"assumptions": {"ranking": "not_applied"}},
                "asset_evidence": {"VALE3": {}, "WEGE3": {}},
                "option_evidence": {"WEGEV500": {"current_quote": {"bid": 1.2}}},
                "limitations": [],
                "source_refs": ["oplab"],
            }

    monkeypatch.setattr(
        fast_dispatch,
        "LiveStrategyComparisonService",
        FakeStrategyService,
    )
    response = FastRouteDispatcher().dispatch(
        task="UC-04: compare Comprar ação em VALE3 e Vender PUT WEGEV500 em WEGE3",
        context={
            "workspace": "Strategy Lab",
            "comparison_assets": ["VALE3", "WEGE3"],
            "strategy_a": "Comprar ação",
            "strategy_b": "Vender PUT",
            "option_b": "WEGEV500",
        },
    )

    assert response is not None
    assert response.status == "COMPLETED"
    assert response.result["fast_route"]["target"] == "strategy_engine"
    assert response.result["option_evidence"]["WEGEV500"]["current_quote"]["bid"] == 1.2


def test_market_price_lookup_uses_current_oplab_quote(monkeypatch):
    current = StockMarketData(
        instrument_id="WEGE3",
        ticker="WEGE3",
        observation_timestamp=fast_dispatch.datetime(2026, 10, 1, 16, 50, tzinfo=fast_dispatch.timezone.utc),
        available_timestamp=fast_dispatch.datetime(2026, 10, 1, 16, 50, tzinfo=fast_dispatch.timezone.utc),
        source="oplab",
        ingested_at=fast_dispatch.datetime(2026, 10, 1, 16, 50, tzinfo=fast_dispatch.timezone.utc),
        source_record_id="WEGE3:current",
        quality_flags=("current_quote",),
        open=49.2,
        high=49.6,
        low=49.1,
        close=49.4,
        volume=2_000_000,
        currency="BRL",
    )
    historical = StockMarketData(
        instrument_id="WEGE3",
        ticker="WEGE3",
        observation_timestamp=fast_dispatch.datetime(2026, 10, 1, 3, 0, tzinfo=fast_dispatch.timezone.utc),
        available_timestamp=fast_dispatch.datetime(2026, 10, 1, 4, 0, tzinfo=fast_dispatch.timezone.utc),
        source="b3_cotahist",
        ingested_at=fast_dispatch.datetime(2026, 10, 1, 4, 0, tzinfo=fast_dispatch.timezone.utc),
        source_record_id="WEGE3:2026-10-01:test",
        open=49.0,
        high=49.5,
        low=48.8,
        close=49.39,
        volume=1_000_000,
        currency="BRL",
    )

    class Current:
        def get_current_quote(self, ticker):
            assert ticker == "WEGE3"
            return current

    class History:
        def get_market_data(self, ticker, start, end):
            assert ticker == "WEGE3"
            return [historical]

    class FakeLiveProviderService:
        def __init__(self):
            self.current_market_provider = Current()
            self.market_provider = History()

    monkeypatch.setattr(fast_dispatch, "LiveProviderService", FakeLiveProviderService)

    response = FastRouteDispatcher().dispatch(task="qual o preço de WEGE3?")

    assert response is not None
    assert response.result["current_market_quote"]["close"] == 49.4
    assert response.result["latest_daily_market_record"]["close"] == 49.39
    assert response.result["as_of"] == current.observation_timestamp
