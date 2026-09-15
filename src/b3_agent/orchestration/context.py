from __future__ import annotations

from datetime import date, datetime
from typing import Any

from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.schemas.position import PortfolioContext


def build_deterministic_context(
    *,
    portfolio_context: PortfolioContext,
    opportunity_set: OpportunitySet,
) -> dict[str, Any]:
    """Build the read-only deterministic context supplied to reasoning.

    Domain objects remain the source of truth. This function only serializes
    them for the reasoning boundary; it does not rank, calculate, or mutate
    portfolio/opportunity facts.
    """
    return {
        "portfolio": _serialize_portfolio(portfolio_context),
        "opportunities": _serialize_opportunities(opportunity_set),
    }


def _serialize_portfolio(context: PortfolioContext) -> dict[str, Any]:
    return {
        "as_of": context.as_of.isoformat(),
        "cash": context.cash,
        "quality_status": context.quality_status,
        "source_refs": list(context.source_refs),
        "positions": [
            {
                "position_id": position.position_id,
                "ticker": position.ticker,
                "instrument_type": position.instrument_type,
                "quantity": position.quantity,
                "average_cost": position.average_cost,
                "strike": position.strike,
                "expiration_date": (
                    position.expiration_date.isoformat()
                    if position.expiration_date
                    else None
                ),
                "option_type": position.option_type,
                "underlying_ticker": position.underlying_ticker,
                "contract_multiplier": position.contract_multiplier,
                "market_price": position.market_price,
                "market_value": position.market_value,
                "source_ref": position.source_ref,
            }
            for position in context.positions
        ],
    }


def _serialize_opportunities(opportunity_set: OpportunitySet) -> dict[str, Any]:
    return {
        "as_of": _isoformat(opportunity_set.as_of),
        "quality_status": opportunity_set.quality_status,
        "ranking_policy_version": opportunity_set.ranking_policy_version,
        "source_refs": list(opportunity_set.source_refs),
        "ranked_opportunities": [
            {
                "opportunity_id": assessment.opportunity_id,
                "eligible": assessment.eligible,
                "rejection_reasons": list(assessment.rejection_reasons),
                "attractiveness": assessment.attractiveness,
                "portfolio_fit": assessment.portfolio_fit,
                "ranking_key": list(assessment.ranking_key),
                "rationale": assessment.rationale,
            }
            for assessment in opportunity_set.ranked_opportunities
        ],
        "rejected_opportunities": [
            {
                "opportunity_id": assessment.opportunity_id,
                "eligible": assessment.eligible,
                "rejection_reasons": list(assessment.rejection_reasons),
                "attractiveness": assessment.attractiveness,
                "portfolio_fit": assessment.portfolio_fit,
                "rationale": assessment.rationale,
            }
            for assessment in opportunity_set.rejected_opportunities
        ],
        "action_candidates": [
            {
                "action_candidate_id": candidate.action_candidate_id,
                "action_type": candidate.action_type,
                "subject_id": candidate.subject_id,
                "priority": candidate.priority,
                "opportunity_refs": list(candidate.opportunity_refs),
                "rationale": candidate.rationale,
                "quality_status": candidate.quality_status,
            }
            for candidate in opportunity_set.action_candidates
        ],
    }


def _isoformat(value: date | datetime) -> str:
    return value.isoformat()
