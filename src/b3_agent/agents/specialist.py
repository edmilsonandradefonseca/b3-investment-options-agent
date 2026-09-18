from __future__ import annotations

import json
from typing import Any

from b3_agent.agents.context import AgentContext
from b3_agent.llm.client import LLMClient

from .specialists import SpecialistAnalysis, SpecialistContext


class SpecialistAgent:
    """Base LLM specialist that interprets only its assigned deterministic slice."""

    agent_name = "specialist"
    focus_keys: tuple[str, ...] = ()

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(self, context: AgentContext | SpecialistContext | dict[str, Any]) -> SpecialistAnalysis:
        if isinstance(context, AgentContext):
            context = SpecialistContext.from_agent_context(context)
        payload = context.to_payload() if isinstance(context, SpecialistContext) else context
        deterministic = payload.get("deterministic_context", {})
        focused = {key: deterministic[key] for key in self.focus_keys if key in deterministic}
        evidence = payload.get("retrieved_evidence", [])
        result = self.llm.complete_json(
            instructions=(
                f"Act as the {self.agent_name} of an investment decision copilot. "
                "Interpret only the supplied deterministic facts relevant to your role "
                "and supplied evidence. Do not invent data, prices, calculations, rankings, "
                "or recommendations. Produce analysis for a separate synthesis agent. "
                "Clearly state uncertainty and risks."
            ),
            input_text=json.dumps(
                {"request": payload.get("request"), "facts": focused, "evidence": evidence},
                ensure_ascii=False,
                default=str,
            ),
            schema_name=f"{self.agent_name}_analysis",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "summary": {"type": "string"},
                    "findings": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "source_refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["summary", "findings", "risks", "evidence_refs", "source_refs"],
            },
        )
        return SpecialistAnalysis(
            agent=self.agent_name,
            summary=result["summary"],
            findings=tuple(result["findings"]),
            risks=tuple(result["risks"]),
            evidence_refs=tuple(result["evidence_refs"]),
            source_refs=tuple(result["source_refs"]),
        )


class MarketAnalysisAgent(SpecialistAgent):
    agent_name = "market_analysis"
    focus_keys = ("market_analysis", "signals", "threats")


class PortfolioAnalysisAgent(SpecialistAgent):
    agent_name = "portfolio_analysis"
    focus_keys = ("portfolio_context", "risk_analysis", "action_candidates")


class OptionsAnalysisAgent(SpecialistAgent):
    agent_name = "options_analysis"
    focus_keys = ("options_analysis", "options_transactions", "opportunities", "action_candidates")
