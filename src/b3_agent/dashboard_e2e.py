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


@dataclass(frozen=True)
class DashboardSnapshot:
    portfolio: PortfolioContext
    portfolio_intelligence: object
    option_transactions: tuple[OptionTransaction, ...]
    opportunities: OpportunitySet


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
        return DashboardSnapshot(
            portfolio=portfolio,
            portfolio_intelligence=intelligence,
            option_transactions=transactions,
            opportunities=opportunities,
        )
