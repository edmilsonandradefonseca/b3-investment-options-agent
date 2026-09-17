from datetime import date

from b3_agent.orchestration.deterministic import (
    build_opportunity_set,
    opportunity_set_state,
)
from b3_agent.schemas.opportunity import Opportunity
from b3_agent.opportunity_pipeline import OpportunityPipeline


AS_OF = date(2026, 9, 15)


def _opportunity(opportunity_id: str) -> Opportunity:
    return Opportunity(
        opportunity_id=opportunity_id,
        ticker="PETR4",
        instrument_type="STOCK",
        action="BUY",
        as_of=AS_OF,
        expected_return=0.12,
        capital_requirement=1000.0,
        evidence_refs=(f"evidence:{opportunity_id}",),
        source_refs=("brapi",),
        quality_status="VALIDATED",
        rationale="Deterministic fixture.",
    )


def test_build_opportunity_set_is_deterministic_and_provider_agnostic() -> None:
    result = build_opportunity_set(
        as_of=AS_OF,
        pipeline=OpportunityPipeline(),
        source_refs=("brapi",),
    )

    assert result.as_of == AS_OF
    assert result.ranked_opportunities == ()
    assert result.quality_status == "VALIDATED"


def test_opportunity_set_state_preserves_object_boundary() -> None:
    opportunity_set = OpportunityPipeline().build((_opportunity("OPP:1"),), as_of=AS_OF)

    state = opportunity_set_state(opportunity_set)

    assert state == {"opportunity_set": opportunity_set}
    assert state["opportunity_set"].ranked_opportunities[0].opportunity_id == "OPP:1"
