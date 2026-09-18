from datetime import date

from b3_agent.opportunity import OpportunityIntelligenceEngine
from b3_agent.orchestration.context import build_deterministic_context
from b3_agent.schemas.opportunity import Opportunity
from b3_agent.schemas.position import PortfolioContext


def test_reasoning_context_preserves_ranked_opportunity_facts() -> None:
    opportunity = Opportunity(
        opportunity_id="ITUB4:BUY:PE",
        ticker="ITUB4",
        instrument_type="STOCK",
        action="BUY",
        as_of=date(2026, 9, 11),
        expected_return=0.25,
        valuation_range_ref="valuation:ITUB4:PE",
        quant_features_ref="quant:ITUB4:2026-09-11",
        capital_requirement=18.0,
        evidence_refs=("valuation:ITUB4:PE", "price:ITUB4:16.0"),
        source_refs=("BRAPI", "VALUATION"),
        quality_status="VALIDATED",
        rationale="Price is below deterministic accumulation threshold.",
    )

    opportunity_set = OpportunityIntelligenceEngine().assess((opportunity,))
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 11),
        positions=(),
        cash=1000.0,
        source_refs=("BTG:Renda Variavel",),
        quality_status="VALIDATED",
    )

    context = build_deterministic_context(
        portfolio_context=portfolio,
        opportunity_set=opportunity_set,
    )

    item = context["opportunities"]["ranked_opportunities"][0]
    assert item["ticker"] == "ITUB4"
    assert item["instrument_type"] == "STOCK"
    assert item["action"] == "BUY"
    assert item["expected_return"] == 0.25
    assert item["capital_requirement"] == 18.0
    assert item["valuation_range_ref"] == "valuation:ITUB4:PE"
    assert item["quant_features_ref"] == "quant:ITUB4:2026-09-11"
    assert item["source_refs"] == ["BRAPI", "VALUATION"]
    assert item["eligible"] is True
