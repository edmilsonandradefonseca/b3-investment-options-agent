from __future__ import annotations

from typing import Any

from b3_agent.schemas.opportunity import OpportunitySet


def opportunity_set_to_context(opportunity_set: OpportunitySet) -> dict[str, Any]:
    """Serialize the deterministic opportunity layer for downstream reasoning.

    The serializer is deliberately loss-aware: it exposes analytical facts and
    provenance only. It does not compute rankings, infer actions, or call an LLM.
    """

    def assessment(item: Any) -> dict[str, Any]:
        return {
            "opportunity_id": item.opportunity_id,
            "ticker": item.ticker,
            "instrument_type": item.instrument_type,
            "action": item.action,
            "as_of": item.as_of.isoformat() if item.as_of else None,
            "eligible": item.eligible,
            "rejection_reasons": list(item.rejection_reasons),
            "attractiveness": item.attractiveness,
            "portfolio_fit": item.portfolio_fit,
            "expected_return": item.expected_return,
            "capital_requirement": item.capital_requirement,
            "liquidity_value": item.liquidity_value,
            "ranking_key": list(item.ranking_key),
            "evidence_refs": list(item.evidence_refs),
            "source_refs": list(item.source_refs),
            "rationale": item.rationale,
            "valuation_range_ref": item.valuation_range_ref,
            "options_analysis_ref": item.options_analysis_ref,
            "quant_features_ref": item.quant_features_ref,
        }

    action_candidates = [
        {
            "action_candidate_id": item.action_candidate_id,
            "action_type": item.action_type,
            "subject_id": item.subject_id,
            "as_of": item.as_of.isoformat() if item.as_of else None,
            "priority": item.priority,
            "opportunity_refs": list(item.opportunity_refs),
            "evidence_refs": list(item.evidence_refs),
            "rationale": item.rationale,
            "quality_status": item.quality_status,
        }
        for item in opportunity_set.action_candidates
    ]

    return {
        "as_of": opportunity_set.as_of.isoformat() if opportunity_set.as_of else None,
        "quality_status": opportunity_set.quality_status,
        "ranking_policy_version": opportunity_set.ranking_policy_version,
        "source_refs": list(opportunity_set.source_refs),
        "ranked_opportunities": [assessment(item) for item in opportunity_set.ranked_opportunities],
        "rejected_opportunities": [assessment(item) for item in opportunity_set.rejected_opportunities],
        "action_candidates": action_candidates,
    }
