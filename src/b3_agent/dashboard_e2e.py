from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from b3_agent.opportunity_pipeline import OpportunityPipeline, StockOpportunityInput
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.options.transactions import OptionsTransactionLoader
from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.schemas.position import PortfolioContext
from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.market_regime import MarketRegime
from b3_agent.schemas.scenario import ScenarioDefinition, StressResult
from b3_agent.schemas.strategy_comparison import StrategyAlternative, StrategyComparison
from b3_agent.experience.regime_engine import MarketRegimeEngine
from b3_agent.scenario import ScenarioStressEngine
from b3_agent.strategy_comparison import StrategyComparisonEngine


@dataclass(frozen=True)
class DashboardSnapshot:
    portfolio: PortfolioContext
    portfolio_intelligence: object
    option_transactions: tuple[OptionTransaction, ...]
    opportunities: OpportunitySet
    strategy_comparisons: tuple[StrategyComparison, ...] = ()
    stress_results: tuple[StressResult, ...] = ()
    market_regime: MarketRegime | None = None


@dataclass(frozen=True)
class DashboardDecisionInputs:
    strategy_pairs: tuple[tuple[StrategyAlternative, StrategyAlternative], ...] = ()
    scenarios: tuple[ScenarioDefinition, ...] = ()
    feature_snapshot: FeatureSnapshot | None = None


@dataclass(frozen=True)
class DashboardOpportunityInputs:
    stock_inputs: tuple[StockOpportunityInput, ...] = ()
    options_analyses: tuple[OptionsAnalysis, ...] = ()
    source_refs: tuple[str, ...] = ()


class DashboardE2EService:
    """Build the deterministic dashboard snapshot from authoritative inputs.

    The service deliberately does not fetch market data or ask an LLM to fill
    missing inputs. Opportunities are therefore empty until validated upstream
    analytical inputs are explicitly supplied to the opportunity pipeline.
    """

    def load(
        self,
        portfolio_path: str | Path,
        *,
        options_path: str | Path | None = None,
        opportunity_inputs: DashboardOpportunityInputs | None = None,
        decision_inputs: DashboardDecisionInputs | None = None,
    ) -> DashboardSnapshot:
        portfolio = BtgRendaVariavelLoader().load(portfolio_path)
        transactions = (
            OptionsTransactionLoader().load(options_path)
            if options_path is not None
            else ()
        )
        intelligence = PortfolioIntelligenceEngine().build(portfolio)
        if opportunity_inputs is None:
            opportunities = OpportunityPipeline().build(
                (),
                as_of=portfolio.as_of,
                source_refs=portfolio.source_refs,
            )
        else:
            opportunities = OpportunityPipeline().build_from_inputs(
                as_of=portfolio.as_of,
                stock_inputs=opportunity_inputs.stock_inputs,
                options_analyses=opportunity_inputs.options_analyses,
                source_refs=tuple(dict.fromkeys(
                    (*portfolio.source_refs, *opportunity_inputs.source_refs)
                )),
            )
        decision_inputs = decision_inputs or DashboardDecisionInputs()
        strategy_comparisons = tuple(StrategyComparisonEngine().compare(left, right) for left, right in decision_inputs.strategy_pairs)
        stress_results = tuple(ScenarioStressEngine().evaluate(portfolio, scenario) for scenario in decision_inputs.scenarios)
        market_regime = MarketRegimeEngine().classify(decision_inputs.feature_snapshot) if decision_inputs.feature_snapshot is not None else None
        return DashboardSnapshot(
            portfolio=portfolio,
            portfolio_intelligence=intelligence,
            option_transactions=transactions,
            opportunities=opportunities,
            strategy_comparisons=strategy_comparisons,
            stress_results=stress_results,
            market_regime=market_regime,
        )
