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
                "as a replacement for deterministic facts or evidence. Do not invent data or calculations. "
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
