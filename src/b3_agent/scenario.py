from __future__ import annotations

from b3_agent.portfolio.capital_risk import CapitalRiskEngine
from b3_agent.schemas.position import PortfolioContext
from b3_agent.schemas.scenario import PositionStress, ScenarioDefinition, StressResult


class ScenarioStressEngine:
    """Deterministic scenario engine over explicit position/ticker shocks.

    This engine does not infer option repricing, FX translation or rate duration.
    It only applies shocks explicitly supplied to position values. More advanced
    pricing models may feed position-specific shocks upstream.
    """

    def evaluate(
        self,
        portfolio: PortfolioContext,
        scenario: ScenarioDefinition,
    ) -> StressResult:
        position_results: list[PositionStress] = []
        base_positions = 0.0
        stressed_positions = 0.0

        for position in portfolio.positions:
            base_value = float(position.market_value or 0.0)
            base_positions += base_value

            shock = scenario.position_value_shocks.get(position.position_id)
            if shock is None:
                key = (position.underlying_ticker or position.ticker).upper()
                shock = scenario.ticker_price_shocks.get(key, 0.0)

            stressed_value = base_value * (1.0 + shock)
            stressed_positions += stressed_value
            position_results.append(
                PositionStress(
                    position_id=position.position_id,
                    ticker=position.ticker,
                    base_value=base_value,
                    stressed_value=stressed_value,
                    pnl_impact=stressed_value - base_value,
                    applied_shock=shock,
                )
            )

        base_total = portfolio.cash + base_positions
        stressed_total = portfolio.cash + stressed_positions
        pnl = stressed_total - base_total
        portfolio_return = pnl / base_total if base_total else None

        capital = CapitalRiskEngine().assess(portfolio)
        gross_exposure = sum(abs(item.stressed_value) for item in position_results)
        max_concentration = 0.0
        if gross_exposure > 0:
            max_concentration = max(
                abs(item.stressed_value) / gross_exposure
                for item in position_results
            )

        sensitivities = {
            f"ticker:{ticker}": shock
            for ticker, shock in sorted(scenario.ticker_price_shocks.items())
        }
        sensitivities.update(
            {
                f"position:{position_id}": shock
                for position_id, shock in sorted(
                    scenario.position_value_shocks.items()
                )
            }
        )

        quality = "VALIDATED"
        if any(position.market_value is None for position in portfolio.positions):
            quality = "WARNING"

        return StressResult(
            scenario_id=scenario.scenario_id,
            as_of=scenario.as_of,
            base_portfolio_value=base_total,
            stressed_portfolio_value=stressed_total,
            portfolio_pnl=pnl,
            portfolio_return=portfolio_return,
            cash=portfolio.cash,
            assignment_capital=capital.assignment_capital,
            cash_after_assignment=capital.cash_after_assignment,
            max_concentration=max_concentration,
            gross_exposure=gross_exposure,
            position_stress=tuple(position_results),
            sensitivities=sensitivities,
            assumptions={
                **scenario.assumptions,
                "stress_method": "explicit-market-value-shock-v1",
                "option_repricing": "not_inferred",
                "rate_fx_commodity_shocks": "context_only_unless_translated_upstream",
            },
            source_refs=scenario.source_refs,
            quality_status=quality,
        )
