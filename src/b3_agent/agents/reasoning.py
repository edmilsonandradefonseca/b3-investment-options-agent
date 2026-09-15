from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

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
    """LLM reasoning over deterministic facts and retrieved investor evidence."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def decide(self, context: dict[str, Any]) -> DecisionProposal:
        result = self.llm.complete_json(
            instructions=(
                "Act as the investment reasoning component of a decision copilot. "
                "Use only the supplied deterministic facts and retrieved evidence. "
                "Do not invent data or calculations. If evidence is insufficient, "
                "prefer WAIT or NO_CHANGE. Return a structured proposal for human review."
            ),
            input_text=json.dumps(context, ensure_ascii=False, default=str),
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
