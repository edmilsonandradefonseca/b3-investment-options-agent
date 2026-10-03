from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from b3_agent.agents.context import AgentContext
from b3_agent.llm.client import LLMClient
from b3_agent.schemas.decision import AlternativeAssessment, DecisionProposal


_DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "alternative_assessments": {
            "type": "array", "maxItems": 20,
            "items": {"type": "object", "additionalProperties": False,
                "properties": {
                    "alternative_id": {"type": "string"},
                    **{key: {"type": "array", "items": {"type": "string"}} for key in (
                        "supporting_evidence", "contradicting_evidence", "decision_implications", "unknowns", "evidence_refs"
                    )},
                },
                "required": ["alternative_id", "supporting_evidence", "contradicting_evidence", "decision_implications", "unknowns", "evidence_refs"],
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
            allowed_ids = list((facts.get('market_analysis') or {}).get('tickers') or {})
        schema = deepcopy(_DECISION_SCHEMA)
        if allowed_ids:
            schema['properties']['alternative_assessments']['items']['properties']['alternative_id']['enum'] = allowed_ids
        result = self.llm.complete_json(
            instructions=(
                "Act as the investment reasoning component of a decision copilot. "
                "Use the supplied deterministic facts and retrieved evidence as the source of truth. "
                "The supplied synthesis is a non-authoritative interpretation of independent specialist analyses: "
                "use it to identify agreements, conflicts, uncertainties and evidence gaps, but do not treat it "
                "as a replacement for deterministic facts or evidence. Optional derived_intelligence is "
                "non-authoritative background context: use it only when consistent with supplied facts/evidence. "
                "Personal history cash flows and net-flat sequences are not verified lifecycle outcomes. "
                "UNKNOWN assignment/expiry/roll statistics must remain unknown; personal frequency is not market probability. "
                "When no specialist synthesis is supplied, synthesize supporting and contradicting evidence directly, "
                "including risks, prior executions, limitations and explicit alternatives for PUT, CALL or stock. "
                "Answer in Portuguese with a decision-specific thesis, not a generic market overview. "
                "In rationale compare every supplied alternative, its strongest supporting and contradicting evidence, "
                "and explain which supplied metric or missing dependency prevents a conclusion. "
                "Use capital_impact and opportunity_cost to discuss the actual tradeoff; when unknown state the "
                "specific missing input, never assume zero costs or available cash. Give observable, sourced "
                "invalidation_conditions rather than vague warnings. Cite supplied identifiers. "
                "Return alternative_assessments for every supplied comparison alternative, or for the requested assets "
                "when no canonical comparison exists. Use their exact supplied alternative_id (or ticker for assets). "
                "Each assessment must separately state supporting_evidence, contradicting_evidence, "
                "decision_implications, unknowns and evidence_refs. These are qualitative interpretations of "
                "supplied facts: do not generate numeric targets, metrics, scores or probabilities. An empty "
                "contradicting_evidence list means none identified in supplied evidence, not absence of risk. "
                "Do not invent data or calculations. A technically ordered list with deferred ranking does not "
                "authorize choosing its first item as the best investment. "
                "If evidence is insufficient, prefer WAIT or NO_CHANGE. Return a structured proposal for human review."
            ),
            input_text=json.dumps(payload, ensure_ascii=False, default=str),
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
    assessments = []
    seen = set()
    for item in values:
        if not isinstance(item, dict):
            raise ValueError('Alternative assessment must be an object')
        identifier = item.get('alternative_id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen or (allowed_ids and identifier not in allowed_ids):
            raise ValueError('Assessment must link to a unique supplied alternative')
        seen.add(identifier)
        fields = {}
        for key in ('supporting_evidence', 'contradicting_evidence', 'decision_implications', 'unknowns', 'evidence_refs'):
            entries = item.get(key)
            if not isinstance(entries, list) or any(not isinstance(value, str) for value in entries):
                raise ValueError('Assessment fields require arrays of text')
            fields[key] = tuple(entries)
        assessments.append(AlternativeAssessment(alternative_id=identifier, **fields))
    return tuple(assessments)
