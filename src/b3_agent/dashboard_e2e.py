from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from b3_agent.opportunity_pipeline import OpportunityPipeline
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
    ) -> DashboardSnapshot:
        portfolio = BtgRendaVariavelLoader().load(portfolio_path)
        transactions = (
            OptionsTransactionLoader().load(options_path)
            if options_path is not None
            else ()
        )
        intelligence = PortfolioIntelligenceEngine().build(portfolio)
        opportunities = OpportunityPipeline().build(
            (),
            as_of=portfolio.as_of,
            source_refs=portfolio.source_refs,
        )
        return DashboardSnapshot(
            portfolio=portfolio,
            portfolio_intelligence=intelligence,
            option_transactions=transactions,
            opportunities=opportunities,
        )
