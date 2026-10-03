from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from b3_agent.agents.context import AgentContext
from b3_agent.llm.client import LLMClient
from b3_agent.schemas.decision import DecisionProposal


_DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
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
                "Do not invent data or calculations. A technically ordered list with deferred ranking does not "
                "authorize choosing its first item as the best investment. "
                "If evidence is insufficient, prefer WAIT or NO_CHANGE. Return a structured proposal for human review."
            ),
            input_text=json.dumps(payload, ensure_ascii=False, default=str),
            schema_name="investment_decision",
            schema=_DECISION_SCHEMA,
        )
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
        )
