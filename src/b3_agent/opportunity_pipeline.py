from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from b3_agent.opportunity import OpportunityIntelligenceEngine
from b3_agent.opportunity_options import OptionsOpportunityProducer
from b3_agent.opportunity_stock import StockOpportunityProducer
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.opportunity import Evidence, Opportunity, OpportunitySet
from b3_agent.schemas.valuation import ValuationRange
from b3_agent.stock_opportunity_service import StockOpportunityService

AS_OF = date | datetime


@dataclass(frozen=True)
class StockOpportunityInput:
    """Validated market observations plus deterministic valuation for one stock."""

    records: tuple[StockMarketData, ...]
    valuation: ValuationRange
    benchmark_records: tuple[StockMarketData, ...] = ()
    source_refs: tuple[str, ...] = ()


class OpportunityPipeline:
    """Assemble and rank deterministic stock and options opportunities.

    Provider adapters and analytical engines remain upstream. This layer accepts
    their validated outputs, converts stock/option analytical inputs through the
    canonical producers, and converges the resulting Opportunity objects through
    the deterministic ranking engine. It never fetches data, performs LLM
    reasoning, or executes trades.
    """

    def __init__(
        self,
        *,
        engine: OpportunityIntelligenceEngine | None = None,
        stock_service: StockOpportunityService | None = None,
        options_producer: OptionsOpportunityProducer | None = None,
    ) -> None:
        self._engine = engine or OpportunityIntelligenceEngine()
        self._stock_service = stock_service or StockOpportunityService(
            producer=StockOpportunityProducer()
        )
        self._options_producer = options_producer or OptionsOpportunityProducer()

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
        available_capital: float | None = None,
        evidence_registry: tuple[Evidence, ...] | None = None,
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
            available_capital=available_capital,
            evidence_registry=evidence_registry,
        )
        return self._with_snapshot(result, as_of=as_of, source_refs=source_refs)

    def build_from_inputs(
        self,
        *,
        as_of: AS_OF,
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
        """Produce canonical opportunities from deterministic analytical inputs."""
        opportunities: list[Opportunity] = []

        for stock_input in stock_inputs:
            opportunities.extend(
                self._stock_service.produce(
                    list(stock_input.records),
                    stock_input.valuation,
                    as_of=as_of,
                    benchmark_records=list(stock_input.benchmark_records) or None,
                    source_refs=stock_input.source_refs,
                )
            )

        for analysis in options_analyses:
            analysis_sources = tuple(dict.fromkeys((*analysis.source_refs, *source_refs)))
            opportunities.extend(
                self._options_producer.produce(
                    analysis,
                    as_of=as_of,
                    source_refs=analysis_sources,
                )
            )

        return self.build(
            opportunities,
            as_of=as_of,
            portfolio_fit=portfolio_fit,
            risk=risk,
            valuation=valuation,
            capital_efficiency=capital_efficiency,
            diversification=diversification,
            relative_assessment=relative_assessment,
            source_refs=source_refs,
            available_capital=available_capital,
        )

    @staticmethod
    def _with_snapshot(
        result: OpportunitySet,
        *,
        as_of: AS_OF | None,
        source_refs: tuple[str, ...],
    ) -> OpportunitySet:
        effective_as_of = as_of if as_of is not None else result.as_of
        combined_sources = tuple(dict.fromkeys((*result.source_refs, *source_refs)))
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
