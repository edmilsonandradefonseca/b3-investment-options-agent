from datetime import date

from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.orchestration.runtime import _apply_portfolio_capital_constraint
from b3_agent.schemas.opportunity import Opportunity
from b3_agent.schemas.position import PortfolioContext


def test_runtime_reapplies_authoritative_portfolio_cash_to_opportunity_set():
    opportunity = Opportunity(
        opportunity_id="SELL_PUT:PETRV300",
        ticker="PETR4",
        instrument_type="OPTION",
        action="SELL_PUT",
        as_of=date(2026, 9, 18),
        expected_return=0.18,
        capital_requirement=3000.0,
        evidence_refs=("options:PETRV300",),
        source_refs=("fixture:BTG",),
        quality_status="VALIDATED",
        rationale="Runtime capital wiring fixture.",
    )
    upstream = OpportunityPipeline().build(
        (opportunity,),
        as_of=date(2026, 9, 18),
        available_capital=80_000.0,
    )
    defaults = {
        "portfolio_context": PortfolioContext(
            as_of=date(2026, 9, 18),
            cash=2_000.0,
            positions=(),
        ),
        "opportunity_set": upstream,
    }

    result = _apply_portfolio_capital_constraint(defaults)
    rebuilt = result["opportunity_set"]

    assert rebuilt.ranked_opportunities == ()
    assert len(rebuilt.rejected_opportunities) == 1
    rejected = rebuilt.rejected_opportunities[0]
    assert rejected.opportunity_id == "SELL_PUT:PETRV300"
    assert "capital_requirement=3000.0 exceeds available_capital=2000.0" in rejected.rejection_reasons
    assert rebuilt.action_candidates == ()


def test_runtime_preserves_affordable_opportunity():
    opportunity = Opportunity(
        opportunity_id="SELL_PUT:PETRV300",
        ticker="PETR4",
        instrument_type="OPTION",
        action="SELL_PUT",
        as_of=date(2026, 9, 18),
        expected_return=0.18,
        capital_requirement=3000.0,
        evidence_refs=("options:PETRV300",),
        source_refs=("fixture:BTG",),
        quality_status="VALIDATED",
        rationale="Runtime capital wiring fixture.",
    )
    upstream = OpportunityPipeline().build(
        (opportunity,),
        as_of=date(2026, 9, 18),
        available_capital=80_000.0,
    )
    defaults = {
        "portfolio_context": PortfolioContext(
            as_of=date(2026, 9, 18),
            cash=3_000.0,
            positions=(),
        ),
        "opportunity_set": upstream,
    }

    rebuilt = _apply_portfolio_capital_constraint(defaults)["opportunity_set"]

    assert len(rebuilt.ranked_opportunities) == 1
    assert rebuilt.ranked_opportunities[0].opportunity_id == "SELL_PUT:PETRV300"
    assert len(rebuilt.action_candidates) == 1
