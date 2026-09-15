from __future__ import annotations

from datetime import date, datetime

from b3_agent.opportunity import OpportunityIntelligenceEngine
from b3_agent.schemas.opportunity import Opportunity, OpportunitySet

AS_OF = date | datetime


class OpportunityPipeline:
    """Assemble already-produced opportunities into the canonical OpportunitySet.

    Producers remain responsible for creating valid stock/option opportunities.
    This layer only converges and ranks them through the deterministic engine.
    It never fetches data, calculates valuation, creates candidates from prices,
    or delegates ranking to an LLM.
    """

    def __init__(self, *, engine: OpportunityIntelligenceEngine | None = None) -> None:
        self._engine = engine or OpportunityIntelligenceEngine()

    def build(
        self,
        opportunities: tuple[Opportunity, ...] | list[Opportunity] = (),
        *,
        as_of: AS_OF | None = None,
        portfolio_fit: dict[str, str] | None = None,
        risk: dict[str, str] | None = None,
        valuation: dict[str, str] | None = None,
        capital_efficiency: dict[str, str] | None = None,
        diversification: dict[str, str] | None = None,
        relative_assessment: dict[str, str] | None = None,
        source_refs: tuple[str, ...] = (),
    ) -> OpportunitySet:
        """Return the deterministic convergence result for supplied opportunities."""
        normalized = tuple(opportunities)
        result = self._engine.assess(
            normalized,
            portfolio_fit=portfolio_fit,
            risk=risk,
            valuation=valuation,
            capital_efficiency=capital_efficiency,
            diversification=diversification,
            relative_assessment=relative_assessment,
        )

        effective_as_of = as_of if as_of is not None else result.as_of
        combined_sources = tuple(
            dict.fromkeys((*result.source_refs, *source_refs))
        )
        if effective_as_of == result.as_of and combined_sources == result.source_refs:
            return result

        return OpportunitySet(
            as_of=effective_as_of,
            ranked_opportunities=result.ranked_opportunities,
            rejected_opportunities=result.rejected_opportunities,
            action_candidates=result.action_candidates,
            relative_opportunities=result.relative_opportunities,
            signals=result.signals,
            threats=result.threats,
            events=result.events,
            impacts=result.impacts,
            ranking_policy_version=result.ranking_policy_version,
            source_refs=combined_sources,
            quality_status=result.quality_status,
        )
