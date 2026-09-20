from __future__ import annotations

from datetime import date, datetime
from typing import Any

from b3_agent.opportunity_pipeline import OpportunityPipeline, StockOpportunityInput
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.schemas.opportunity import OpportunitySet

AS_OF = date | datetime


def build_opportunity_set(
    *,
    as_of: AS_OF,
    pipeline: OpportunityPipeline | None = None,
    stock_inputs: tuple[StockOpportunityInput, ...] = (),
    options_analyses: tuple[OptionsAnalysis, ...] = (),
    portfolio_fit: dict[str, str] | None = None,
    risk: dict[str, str] | None = None,
    valuation: dict[str, str] | None = None,
    capital_efficiency: dict[str, str] | None = None,
    diversification: dict[str, str] | None = None,
    relative_assessment: dict[str, str] | None = None,
    source_refs: tuple[str, ...] = (),
    available_capital: float | None = None,
) -> OpportunitySet:
    """Build the deterministic OpportunitySet consumed by the V3.1 graph.

    Provider adapters are intentionally absent here: BRAPI/OpLab outputs must
    first pass their adapters and point-in-time validation, then arrive as typed
    analytical inputs. This function only composes deterministic producers.
    """
    producer = pipeline or OpportunityPipeline()
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
        available_capital=available_capital,
    )


def opportunity_set_state(opportunity_set: OpportunitySet) -> dict[str, Any]:
    """Return the minimal V3.1 state payload for deterministic opportunities."""
    return {"opportunity_set": opportunity_set}
