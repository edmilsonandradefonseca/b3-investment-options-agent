from datetime import date

from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.orchestration.opportunity_context import opportunity_set_to_context
from b3_agent.schemas.opportunity import Opportunity


AS_OF = date(2026, 9, 15)


def test_opportunity_set_context_preserves_ranked_facts_candidates_and_provenance() -> None:
    opportunity = Opportunity(
        opportunity_id="OPP:PETR4:BUY",
        ticker="PETR4",
        instrument_type="STOCK",
        action="BUY",
        as_of=AS_OF,
        expected_return=0.12,
        capital_requirement=1000.0,
        liquidity_value=2500.0,
        evidence_refs=("market:petr4",),
        source_refs=("brapi",),
        quality_status="VALIDATED",
        rationale="Deterministic stock opportunity.",
    )
    opportunity_set = OpportunityPipeline().build(
        (opportunity,),
        source_refs=("pipeline",),
    )

    context = opportunity_set_to_context(opportunity_set)

    assert context["as_of"] == "2026-09-15"
    assert context["quality_status"] == "VALIDATED"
    assert context["ranking_policy_version"] == "1.0"
    assert context["source_refs"] == ["brapi", "pipeline"]
    assert context["ranked_opportunities"][0]["opportunity_id"] == "OPP:PETR4:BUY"
    assert context["ranked_opportunities"][0]["ticker"] == "PETR4"
    assert context["ranked_opportunities"][0]["action"] == "BUY"
    assert context["ranked_opportunities"][0]["expected_return"] == 0.12
    assert context["ranked_opportunities"][0]["evidence_refs"] == ["market:petr4"]
    assert context["ranked_opportunities"][0]["source_refs"] == ["brapi"]
    assert context["action_candidates"][0]["action_type"] == "BUY"
    assert context["action_candidates"][0]["opportunity_refs"] == ["OPP:PETR4:BUY"]
    assert context["rejected_opportunities"] == []
