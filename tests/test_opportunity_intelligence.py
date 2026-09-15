from datetime import date

from b3_agent.opportunity import OpportunityIntelligenceEngine
from b3_agent.schemas.opportunity import Opportunity


AS_OF = date(2026, 9, 11)


def opportunity(opportunity_id: str, *, expected_return=None, quality="VALIDATED", action="BUY"):
    return Opportunity(
        opportunity_id=opportunity_id,
        ticker="PETR4",
        instrument_type="STOCK",
        action=action,
        as_of=AS_OF,
        expected_return=expected_return,
        evidence_refs=(f"evidence:{opportunity_id}",),
        source_refs=("test",),
        quality_status=quality,
    )


def test_policy_is_lexicographic_before_expected_return():
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (opportunity("B", expected_return=0.50), opportunity("A", expected_return=0.10)),
        portfolio_fit={"A": "GOOD", "B": "NEUTRAL"},
    )
    assert [item.opportunity_id for item in result.ranked_opportunities] == ["A", "B"]


def test_expected_return_descending_when_prior_dimensions_tie():
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (opportunity("LOW", expected_return=0.10), opportunity("HIGH", expected_return=0.30)),
    )
    assert [item.opportunity_id for item in result.ranked_opportunities] == ["HIGH", "LOW"]


def test_missing_expected_return_is_not_treated_as_zero_and_ranks_last():
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (opportunity("UNKNOWN", expected_return=None), opportunity("KNOWN", expected_return=0.0)),
    )
    assert [item.opportunity_id for item in result.ranked_opportunities] == ["KNOWN", "UNKNOWN"]


def test_rejected_opportunity_is_separated_with_reason():
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (opportunity("OK", expected_return=0.10), opportunity("BAD", quality="REJECTED")),
    )
    assert [item.opportunity_id for item in result.ranked_opportunities] == ["OK"]
    assert [item.opportunity_id for item in result.rejected_opportunities] == ["BAD"]
    assert result.rejected_opportunities[0].rejection_reasons == ("quality_status=REJECTED",)
    assert result.quality_status == "WARNING"


def test_unsupported_action_is_rejected():
    engine = OpportunityIntelligenceEngine()
    result = engine.assess((opportunity("BAD", action="HOLD"),))
    assert result.ranked_opportunities == ()
    assert result.rejected_opportunities[0].eligible is False
    assert "unsupported action=HOLD" in result.rejected_opportunities[0].rejection_reasons


def test_ticker_id_is_final_tiebreak():
    engine = OpportunityIntelligenceEngine()
    result = engine.assess(
        (opportunity("B", expected_return=0.20), opportunity("A", expected_return=0.20)),
    )
    assert [item.opportunity_id for item in result.ranked_opportunities] == ["A", "B"]
