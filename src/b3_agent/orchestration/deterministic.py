from __future__ import annotations

from datetime import date, datetime
from typing import Any

from b3_agent.opportunity_pipeline import OpportunityPipeline, StockOpportunityInput
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.schemas.position import PortfolioContext

AS_OF = date | datetime


def build_opportunity_set(
    *,
    as_of: AS_OF,
    pipeline: OpportunityPipeline | None = None,
    stock_inputs: tuple[StockOpportunityInput, ...] = (),
    options_analyses: tuple[OptionsAnalysis, ...] = (),
    portfolio_context: PortfolioContext | None = None,
    portfolio_fit: dict[str, str] | None = None,
    risk: dict[str, str] | None = None,
    valuation: dict[str, str] | None = None,
    capital_efficiency: dict[str, str] | None = None,
    diversification: dict[str, str] | None = None,
    relative_assessment: dict[str, str] | None = None,
    source_refs: tuple[str, ...] = (),
    available_capital: float | None = None,
) -> OpportunitySet:
    producer = pipeline or OpportunityPipeline()
    effective_capital = (
        available_capital
        if available_capital is not None
        else portfolio_context.cash if portfolio_context is not None else None
    )
    return producer.build_from_inputs(
        as_of=as_of,
        stock_inputs=stock_inputs,
        options_analyses=options_analyses,
        portfolio_fit=portfolio_fit,
        risk=risk,
        valuation=valuation,
        capital_efficiency=capital_efficiency,
        diversification=diversification,
        relative_assessment=relative_assessment,
        source_refs=source_refs,
        available_capital=effective_capital,
    )


def opportunity_set_state(opportunity_set: OpportunitySet) -> dict[str, Any]:
    return {"opportunity_set": opportunity_set}
