from datetime import date

from b3_agent.opportunity import OpportunityIntelligenceEngine
from b3_agent.schemas.opportunity import Opportunity


def opportunity(opportunity_id: str, expected_return: float | None) -> Opportunity:
    return Opportunity(
        opportunity_id=opportunity_id,
        ticker="PETR4",
        instrument_type="OPTION",
        action="SELL_PUT",
        as_of=date(2026, 9, 15),
        expected_return=expected_return,
        evidence_refs=(f"evidence:{opportunity_id}",),
        source_refs=("TEST",),
    )


def test_expected_return_precedes_capital_efficiency() -> None:
    engine = OpportunityIntelligenceEngine()
    opportunities = (
        opportunity("LOW_RETURN", 0.10),
        opportunity("HIGH_RETURN", 0.20),
    )

    result = engine.assess(
        opportunities,
        capital_efficiency={
            "LOW_RETURN": "HIGH",
            "HIGH_RETURN": "LOW",
        },
    )

    assert [item.opportunity_id for item in result.ranked_opportunities] == [
        "HIGH_RETURN",
        "LOW_RETURN",
    ]


def test_expected_return_none_ranks_after_numeric_values() -> None:
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (
            opportunity("NO_RETURN", None),
            opportunity("RETURN", 0.01),
        )
    )

    assert [item.opportunity_id for item in result.ranked_opportunities] == [
        "RETURN",
        "NO_RETURN",
    ]


def test_rejected_opportunity_is_kept_separate() -> None:
    engine = OpportunityIntelligenceEngine()
    rejected = Opportunity(
        opportunity_id="BAD",
        ticker="PETR4",
        instrument_type="OPTION",
        action="HOLD_WAIT",
        as_of=date(2026, 9, 15),
    )

    result = engine.assess((rejected, opportunity("GOOD", 0.10)))

    assert [item.opportunity_id for item in result.ranked_opportunities] == ["GOOD"]
    assert [item.opportunity_id for item in result.rejected_opportunities] == ["BAD"]
    assert result.rejected_opportunities[0].rejection_reasons == (
        "unsupported action=HOLD_WAIT",
    )
    assert result.quality_status == "WARNING"


def test_available_capital_rejects_unaffordable_option() -> None:
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (Opportunity(
            opportunity_id="SELL_PUT:PETRV300",
            ticker="PETR4",
            instrument_type="OPTION",
            action="SELL_PUT",
            as_of=date(2026, 9, 18),
            capital_requirement=3000.0,
            expected_return=0.18,
            evidence_refs=("options:PETRV300",),
            source_refs=("fixture:BTG",),
        ),),
        available_capital=2000.0,
    )

    assert result.ranked_opportunities == ()
    assert [item.opportunity_id for item in result.rejected_opportunities] == ["SELL_PUT:PETRV300"]
    assert result.rejected_opportunities[0].eligible is False
    assert result.rejected_opportunities[0].rejection_reasons == (
        "capital_requirement=3000.0 exceeds available_capital=2000.0",
    )
    assert result.action_candidates == ()
    assert result.quality_status == "WARNING"


def test_available_capital_allows_affordable_option() -> None:
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (opportunity("SELL_PUT:PETRV300", 0.18),),
        available_capital=3000.0,
    )

    assert [item.opportunity_id for item in result.ranked_opportunities] == ["SELL_PUT:PETRV300"]
    assert result.rejected_opportunities == ()
    assert result.action_candidates[0].action_type == "SELL_PUT"


def test_missing_evidence_rejects_opportunity_and_action_candidate() -> None:
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (
            Opportunity(
                opportunity_id="SELL_PUT:NO_EVIDENCE",
                ticker="PETR4",
                instrument_type="OPTION",
                action="SELL_PUT",
                as_of=date(2026, 9, 18),
                capital_requirement=3000.0,
                expected_return=0.18,
                source_refs=("fixture:BTG",),
                quality_status="VALIDATED",
            ),
        ),
        available_capital=80000.0,
    )

    assert result.ranked_opportunities == ()
    assert [item.opportunity_id for item in result.rejected_opportunities] == [
        "SELL_PUT:NO_EVIDENCE"
    ]
    assert result.rejected_opportunities[0].rejection_reasons == (
        "evidence_refs=EMPTY",
    )
    assert result.action_candidates == ()
    assert result.quality_status == "WARNING"


def test_valid_evidence_allows_action_candidate() -> None:
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (
            Opportunity(
                opportunity_id="SELL_PUT:WITH_EVIDENCE",
                ticker="PETR4",
                instrument_type="OPTION",
                action="SELL_PUT",
                as_of=date(2026, 9, 18),
                capital_requirement=3000.0,
                expected_return=0.18,
                evidence_refs=("options:PETRV300",),
                source_refs=("fixture:BTG",),
                quality_status="VALIDATED",
            ),
        ),
        available_capital=80000.0,
    )

    assert [item.opportunity_id for item in result.ranked_opportunities] == [
        "SELL_PUT:WITH_EVIDENCE"
    ]
    assert result.action_candidates[0].evidence_refs == ("options:PETRV300",)
