from datetime import date

from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.schemas.opportunity import Opportunity

AS_OF = date(2026, 9, 15)


def make_opportunity(
    opportunity_id: str,
    *,
    ticker: str = "PETR4",
    action: str = "BUY",
    expected_return: float | None = 0.10,
    source_refs: tuple[str, ...] = ("deterministic",),
) -> Opportunity:
    return Opportunity(
        opportunity_id=opportunity_id,
        ticker=ticker,
        instrument_type="STOCK",
        action=action,
        as_of=AS_OF,
        expected_return=expected_return,
        capital_requirement=1000.0,
        evidence_refs=(f"evidence:{opportunity_id}",),
        source_refs=source_refs,
        quality_status="VALIDATED",
        rationale="Golden deterministic opportunity.",
    )


def test_pipeline_assembles_and_ranks_supplied_opportunities() -> None:
    opportunities = (
        make_opportunity("LOW", expected_return=0.10),
        make_opportunity("HIGH", expected_return=0.30),
    )

    result = OpportunityPipeline().build(
        opportunities,
        source_refs=("pipeline",),
    )

    assert [item.opportunity_id for item in result.ranked_opportunities] == [
        "HIGH",
        "LOW",
    ]
    assert result.rejected_opportunities == ()
    assert result.quality_status == "VALIDATED"
    assert result.source_refs == ("deterministic", "pipeline")


def test_pipeline_preserves_rejections_and_quality_warning() -> None:
    result = OpportunityPipeline().build(
        (
            make_opportunity("GOOD"),
            make_opportunity("BAD", action="HOLD_WAIT"),
        )
    )

    assert [item.opportunity_id for item in result.ranked_opportunities] == ["GOOD"]
    assert [item.opportunity_id for item in result.rejected_opportunities] == ["BAD"]
    assert result.rejected_opportunities[0].eligible is False
    assert result.quality_status == "WARNING"


def test_pipeline_can_override_snapshot_as_of_without_changing_opportunity_facts() -> None:
    result = OpportunityPipeline().build(
        (make_opportunity("A"),),
        as_of=date(2026, 9, 16),
    )

    assert result.as_of == date(2026, 9, 16)
    assert result.ranked_opportunities[0].as_of == AS_OF
    assert result.ranked_opportunities[0].ticker == "PETR4"
    assert result.ranked_opportunities[0].action == "BUY"


def test_pipeline_empty_input_is_a_valid_empty_snapshot() -> None:
    result = OpportunityPipeline().build(as_of=AS_OF)

    assert result.as_of == AS_OF
    assert result.ranked_opportunities == ()
    assert result.rejected_opportunities == ()
    assert result.quality_status == "VALIDATED"
