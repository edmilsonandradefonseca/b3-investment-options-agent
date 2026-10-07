from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from b3_agent.agents.context import AgentContext
from b3_agent.agents.prompt_context import serialize_senior_context
from b3_agent.llm.client import LLMClient
from b3_agent.schemas.decision import AlternativeAssessment, DecisionProposal


_DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "alternative_assessments": {
            "type": "array", "maxItems": 40,
            "items": {"type": "object", "additionalProperties": False,
                "properties": {
                    "alternative_id": {"type": "string"},
                    "priority_rank": {"type": "integer", "minimum": 0, "maximum": 40},
                    **{key: {"type": "array", "items": {"type": "string"}} for key in (
                        "supporting_evidence", "contradicting_evidence", "decision_implications", "unknowns", "evidence_refs"
                    )},
                },
                "required": ["alternative_id", "priority_rank", "supporting_evidence", "contradicting_evidence", "decision_implications", "unknowns", "evidence_refs"],
            },
        },
        "action": {"type": "string"},
        "subject_id": {"type": "string"},
        "thesis": {"type": "string"},
        "rationale": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "opportunity_cost": {"type": "string"},
        "capital_impact": {"type": "string"},
        "confidence": {"type": "string"},
        "invalidation_conditions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "action", "subject_id", "thesis", "rationale", "evidence_refs",
        "risks", "opportunity_cost", "capital_impact", "confidence",
        "invalidation_conditions",
    ],
}


class InvestmentReasoningAgent:
    """LLM reasoning over deterministic facts, synthesis, and retrieved evidence."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def decide(self, context: AgentContext | dict[str, Any]) -> DecisionProposal:
        """Produce a structured proposal without changing upstream facts."""
        payload = context.to_payload() if isinstance(context, AgentContext) else context
        facts = payload.get('deterministic_context') or {}
        workspace = facts.get('workspace_result') or {}
        alternatives = (workspace.get('strategy_comparison') or {}).get('alternatives') or []
        allowed_ids = [item['alternative_id'] for item in alternatives if isinstance(item, dict) and isinstance(item.get('alternative_id'), str)]
        if not allowed_ids:
            screen_rows = (
                ((workspace.get('opportunity_screen') or {}).get('rows') or [])
                if isinstance(workspace.get('opportunity_screen'), dict)
                else []
            )
            if screen_rows:
                allowed_ids = [
                    item.get('ticker') for item in screen_rows
                    if isinstance(item, dict) and item.get('discovery_eligible') is True
                    and isinstance(item.get('ticker'), str)
                ]
            else:
                allowed_ids = list((facts.get('market_analysis') or {}).get('tickers') or {})
        schema = deepcopy(_DECISION_SCHEMA)
        if allowed_ids:
            schema['properties']['alternative_assessments']['items']['properties']['alternative_id']['enum'] = allowed_ids
            schema['required'].append('alternative_assessments')
        else:
            # Preserve the legacy shape when no alternatives/assets were supplied.
            # Strict JSON-schema clients require every declared property to be required.
            schema['properties'].pop('alternative_assessments')
        result = self.llm.complete_json(
            instructions=(
                "Act as the investment reasoning component of a decision copilot. "
                "An object containing only $b3_context_ref is an exact repeated block: resolve its JSON Pointer "
                "against this input and use the complete referenced facts, including UNKNOWN and source dates. "
                "Use the supplied deterministic facts and retrieved evidence as the source of truth. "
                "The supplied synthesis is a non-authoritative interpretation of independent specialist analyses: "
                "use it to identify agreements, conflicts, uncertainties and evidence gaps, but do not treat it "
                "as a replacement for deterministic facts or evidence. Optional derived_intelligence is "
                "non-authoritative background context: use it only when consistent with supplied facts/evidence. "
                "Personal history cash flows and net-flat sequences are not verified lifecycle outcomes. "
                "UNKNOWN assignment/expiry/roll statistics must remain unknown; personal frequency is not market probability. "
                "When no specialist synthesis is supplied, synthesize supporting and contradicting evidence directly, "
                "including risks, prior executions, limitations and explicit alternatives for PUT, CALL or stock. "
                "For Opportunities, assess the complete supplied stock universe using current dated news/events, "
                "the supplied share-price history and observed risk, available fundamentals, B3 PRE/DIC future-yield "
                "curve vertices, portfolio exposure and source dates. Explain when each factor is unavailable; "
                "do not infer causal effects from co-movement or treat a missing factor as neutral. "
                "In each alternative_assessments item, priority_rank is 1..N only for a specific, material, "
                "currently evidenced stock opportunity whose supporting evidence outweighs its contradictions; "
                "rank those items by urgency/materiality, not by volatility, liquidity, target upside alone, or "
                "ticker order. Set priority_rank=0 for monitor-only, incomplete, contradicted or unsupported theses. "
                "Use contiguous ranks starting at 1, and use no positive rank when no thesis qualifies. "
                "A priority rank means review priority, never a BUY recommendation or expected-return forecast. "
                "Answer in Portuguese with a decision-specific thesis, not a generic market overview. "
                "In rationale compare every supplied alternative, its strongest supporting and contradicting evidence, "
                "and explain which supplied metric or missing dependency prevents a conclusion. "
                "Use capital_impact and opportunity_cost to discuss the actual tradeoff; when unknown state the "
                "specific missing input, never assume zero costs or available cash. Give observable, sourced "
                "invalidation_conditions rather than vague warnings. Cite supplied identifiers. "
                "When the schema includes alternative_assessments, return it for every supplied comparison alternative, or for the requested assets "
                "when no canonical comparison exists. Use their exact supplied alternative_id (or ticker for assets). "
                "Each assessment must separately state supporting_evidence, contradicting_evidence, "
                "decision_implications, unknowns and evidence_refs. These are qualitative interpretations of "
                "supplied facts: do not generate numeric targets, metrics, scores or probabilities. An empty "
                "contradicting_evidence list means none identified in supplied evidence, not absence of risk. "
                "A stock opportunity_screen rank measures only its explicitly named observed risk/liquidity objective. "
                "It is not a valuation, forecast, economic BUY preference or expected return. Discuss its missing "
                "economic dimensions and conditional nature rather than turning a low-volatility rank into a BUY recommendation. "
                "When economic_evidence or economic_target_ranking is supplied, discuss each institution, report date and horizon separately. "
                "Target price-only upside is an institutional opinion, not expected total return. Announced eligible gross income is conditional, "
                "historical paid yield is descriptive, and missing distribution coverage is not zero income. Explain modeled position quantity, "
                "recorded-cash funding limits and related options; do not call gross asset share NAV or sector diversification. "
                "When economic_decision is supplied, explain integer sizing, residual cash, user costs, scenario P&L and opportunity cost. "
                "Its terminal prices, dividend amounts and cost assumptions come from the user, not a market forecast. "
                "A conditional maximin rank applies only to that supplied scenario set; never turn it into a general BUY recommendation. "
                "Missing costs or scenario dividends remain UNKNOWN, and observed historical distributions are not forward dividend yield. "
                "Do not invent data or calculations. A technically ordered list with deferred ranking does not "
                "authorize choosing its first item as the best investment. "
                "If evidence is insufficient, prefer WAIT or NO_CHANGE. Return a structured proposal for human review."
            ),
            input_text=serialize_senior_context(payload),
            schema_name="investment_decision",
            schema=schema,
        )
        assessments = _parse_assessments(result.get("alternative_assessments", []), allowed_ids)
        return DecisionProposal(
            action=result["action"],
            subject_id=result["subject_id"],
            thesis=result["thesis"],
            rationale=result["rationale"],
            evidence_refs=tuple(result["evidence_refs"]),
            risks=tuple(result["risks"]),
            opportunity_cost=result["opportunity_cost"],
            capital_impact=result["capital_impact"],
            confidence=result["confidence"],
            invalidation_conditions=tuple(result["invalidation_conditions"]),
            as_of=datetime.now(timezone.utc),
            alternative_assessments=assessments,
        )


def _parse_assessments(values: Any, allowed_ids: list[str]) -> tuple[AlternativeAssessment, ...]:
    if not isinstance(values, list) or len(values) > 20:
        raise ValueError('Invalid alternative assessments')
    if values and not allowed_ids:
        raise ValueError('No supplied alternatives to assess')
    assessments = []
    seen = set()
    seen_ranks = set()
    for item in values:
        if not isinstance(item, dict):
            raise ValueError('Alternative assessment must be an object')
        identifier = item.get('alternative_id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen or (allowed_ids and identifier not in allowed_ids):
            raise ValueError('Assessment must link to a unique supplied alternative')
        seen.add(identifier)
        priority_rank = item.get('priority_rank', 0)
        if isinstance(priority_rank, bool) or not isinstance(priority_rank, int) or not 0 <= priority_rank <= 40:
            raise ValueError('Assessment priority rank must be an integer from 0 to 40')
        if priority_rank and priority_rank in seen_ranks:
            raise ValueError('Assessment priority ranks must be unique')
        if priority_rank:
            seen_ranks.add(priority_rank)
        fields = {}
        for key in ('supporting_evidence', 'contradicting_evidence', 'decision_implications', 'unknowns', 'evidence_refs'):
            entries = item.get(key)
            if not isinstance(entries, list) or any(not isinstance(value, str) for value in entries):
                raise ValueError('Assessment fields require arrays of text')
            fields[key] = tuple(entries)
        assessments.append(AlternativeAssessment(alternative_id=identifier, priority_rank=priority_rank, **fields))
    return tuple(assessments)
