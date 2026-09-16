from __future__ import annotations

import json
from typing import Any

from b3_agent.agents.context import AgentContext
from b3_agent.llm.client import LLMClient


_SPECIALIST_KEYS = (
    "market_agent_analysis",
    "portfolio_agent_analysis",
    "options_agent_analysis",
)


class SynthesisAgent:
    """Reconciles independent specialist analyses into a decision-ready context.

    The synthesis layer does not calculate, rank opportunities, fetch provider data,
    or execute trades. It makes conflicts and uncertainty explicit for the existing
    deterministic risk gate and decision schema.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def synthesize(self, context: AgentContext | dict[str, Any]) -> dict[str, Any]:
        payload = context.to_payload() if isinstance(context, AgentContext) else context
        facts = payload.get("deterministic_context", {})
        if not isinstance(facts, dict):
            facts = {}
        deterministic_facts = {
            key: value for key, value in facts.items() if key not in _SPECIALIST_KEYS
        }
        specialist_outputs = {
            key: facts[key] for key in _SPECIALIST_KEYS if key in facts
        }
        result = self.llm.complete_json(
            instructions=(
                "Act as the synthesis/committee component of an investment decision copilot. "
                "Reconcile the supplied independent specialist analyses against the supplied "
                "deterministic facts and evidence. Do not invent data, perform new calculations, "
                "rerank opportunities, or execute trades. Identify agreements, conflicts, material "
                "uncertainties and evidence gaps. This is decision-support context for a separate "
                "decision proposal and human review."
            ),
            input_text=json.dumps(
                {
                    "request": payload.get("request"),
                    "deterministic_facts": deterministic_facts,
                    "specialist_analyses": specialist_outputs,
                    "retrieved_evidence": payload.get("retrieved_evidence", []),
                },
                ensure_ascii=False,
                default=str,
            ),
            schema_name="investment_synthesis",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "summary": {"type": "string"},
                    "agreements": {"type": "array", "items": {"type": "string"}},
                    "conflicts": {"type": "array", "items": {"type": "string"}},
                    "uncertainties": {"type": "array", "items": {"type": "string"}},
                    "evidence_gaps": {"type": "array", "items": {"type": "string"}},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "summary", "agreements", "conflicts", "uncertainties",
                    "evidence_gaps", "evidence_refs",
                ],
            },
        )
        return {
            "summary": result["summary"],
            "agreements": list(result["agreements"]),
            "conflicts": list(result["conflicts"]),
            "uncertainties": list(result["uncertainties"]),
            "evidence_gaps": list(result["evidence_gaps"]),
            "evidence_refs": list(result["evidence_refs"]),
        }
