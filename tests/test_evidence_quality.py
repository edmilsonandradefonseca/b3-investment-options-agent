from datetime import date

from b3_agent.opportunity import OpportunityIntelligenceEngine
from b3_agent.schemas.opportunity import Evidence, Opportunity


AS_OF = date(2026, 9, 18)


def _opportunity(evidence_refs=("evidence:PETRV300",)):
    return Opportunity(
        opportunity_id="SELL_PUT:PETRV300",
        ticker="PETR4",
        instrument_type="OPTION",
        action="SELL_PUT",
        as_of=AS_OF,
        expected_return=0.18,
        capital_requirement=3000.0,
        evidence_refs=evidence_refs,
        source_refs=("fixture:BTG",),
    )


def _evidence(evidence_id="evidence:PETRV300", quality_status="VALIDATED"):
    return Evidence(
        evidence_id=evidence_id,
        evidence_type="OPTIONS_ANALYSIS",
        subject_id="PETRV300",
        as_of=AS_OF,
        value={"annualized_return": 0.18},
        source_refs=("fixture:BTG",),
        quality_status=quality_status,
    )


def test_missing_evidence_reference_rejects_action_candidate():
    result = OpportunityIntelligenceEngine().assess(
        (_opportunity(),),
        evidence_registry=(),
    )

    assert len(result.ranked_opportunities) == 0
    assert len(result.action_candidates) == 0
    rejected = result.rejected_opportunities[0]
    assert rejected.eligible is False
    assert "evidence_ref_missing=evidence:PETRV300" in rejected.rejection_reasons


def test_rejected_evidence_quality_rejects_action_candidate():
    result = OpportunityIntelligenceEngine().assess(
        (_opportunity(),),
        evidence_registry=(_evidence(quality_status="REJECTED"),),
    )

    assert len(result.ranked_opportunities) == 0
    assert len(result.action_candidates) == 0
    assert "evidence_quality=REJECTED:evidence:PETRV300" in result.rejected_opportunities[0].rejection_reasons


def test_validated_evidence_allows_action_candidate():
    result = OpportunityIntelligenceEngine().assess(
        (_opportunity(),),
        evidence_registry=(_evidence(),),
    )

    assert len(result.ranked_opportunities) == 1
    assert len(result.action_candidates) == 1
    assert result.ranked_opportunities[0].eligible is True

def test_future_evidence_rejects_opportunity():
    evidence = _evidence()
    future = Evidence(
        evidence_id=evidence.evidence_id,
        evidence_type=evidence.evidence_type,
        subject_id=evidence.subject_id,
        as_of=date(2026, 9, 19),
        value=evidence.value,
        source_refs=evidence.source_refs,
        quality_status=evidence.quality_status,
    )
    result = OpportunityIntelligenceEngine().assess(
        (_opportunity(),),
        evidence_registry=(future,),
    )

    assert "evidence_as_of_after_opportunity=evidence:PETRV300" in result.rejected_opportunities[0].rejection_reasons


def test_evidence_without_source_refs_rejects_opportunity():
    evidence = _evidence()
    without_sources = Evidence(
        evidence_id=evidence.evidence_id,
        evidence_type=evidence.evidence_type,
        subject_id=evidence.subject_id,
        as_of=evidence.as_of,
        value=evidence.value,
        source_refs=(),
        quality_status=evidence.quality_status,
    )
    result = OpportunityIntelligenceEngine().assess(
        (_opportunity(),),
        evidence_registry=(without_sources,),
    )

    assert "evidence_source_refs=EMPTY:evidence:PETRV300" in result.rejected_opportunities[0].rejection_reasons
