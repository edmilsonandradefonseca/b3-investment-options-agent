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
                "uncertainties and evidence gaps. Optional derived intelligence is non-authoritative "
                "and must never override deterministic facts or Evidence. This is decision-support context for a separate "
                "decision proposal and human review. Answer in clear Brazilian Portuguese for an individual investor. Keep the summary to at most three short sentences and 65 words. Start with \"Leitura prática:\" and state what the supplied evidence supports now, then the most important reason and the specific missing item that could change the decision. Prefer concrete supplied facts with dates/source over abstract labels. Explain any necessary technical term on first use: valuation means an estimate of fair value; executable option chain means current bid/ask, volume and contract details. Never write vague phrases such as \"observational financial evidence\", \"current thesis missing\", or \"portfolio impact not reconciled\" without saying exactly which supplied datum is missing or conflicts. If the evidence does not support a transaction, say plainly that no new operation is justified now and identify the blocker; do not imply a buy/sell recommendation from incomplete evidence. Name exact source conflicts and values only when present in deterministic facts. Do not say evidence is absent when search status only indicates incomplete coverage. This synthesis is context, not the final portfolio action; do not override a separate proposal or deterministic gate. Compare all supplied alternatives "
                "explicitly; explain material supporting and contradicting evidence and the decision consequence "
                "of each conflict or gap. Do not equate missing information with absence of risk, use generic "
                "disclaimers in place of analysis, or present a deferred technical order as economic ranking."
            ),
            input_text=json.dumps(
                {
                    "request": payload.get("request"),
                    "deterministic_facts": deterministic_facts,
                    "specialist_analyses": specialist_outputs,
                    "retrieved_evidence": payload.get("retrieved_evidence", []),
                    "derived_intelligence": payload.get("derived_intelligence", {}),
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
