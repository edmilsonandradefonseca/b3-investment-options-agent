from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from b3_agent.agents.context import AgentContext
from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.knowledge.retrieval import ObsidianRetriever

from .contracts import B3State


def build_workflow(
    *,
    retriever: ObsidianRetriever,
    reasoning_agent: InvestmentReasoningAgent,
    risk_validator: RiskValidator,
):
    """Build the LangGraph workflow behind the V3.1 orchestrator contract."""

    def retrieve(state: B3State) -> dict[str, Any]:
        question = state.get("user_question") or state.get("request")
        if not question:
            raise ValueError("user_question is required")
        records = retriever.retrieve(question, top_k=5)
        evidence = [
            {
                "source_ref": item.source_ref,
                "relative_path": item.relative_path,
                "snippet": item.snippet,
                "score": item.score,
            }
            for item in records
        ]
        return {"evidence": evidence, "user_question": question}

    def reason(state: B3State) -> dict[str, Any]:
        request = state.get("user_question") or state.get("request")
        if not request:
            raise ValueError("user_question is required")
        deterministic_context: dict[str, Any] = {
            key: state[key]
            for key in (
                "portfolio_context",
                "signals",
                "threats",
                "opportunities",
                "action_candidates",
                "fundamental_analysis",
                "market_analysis",
                "options_analysis",
                "risk_analysis",
            )
            if key in state
        }
        legacy_context = state.get("deterministic_context") or {}
        for key, value in legacy_context.items():
            deterministic_context.setdefault(key, value)
        context = AgentContext(
            request=request,
            deterministic_context=deterministic_context,
            retrieved_evidence=tuple(state.get("evidence", [])),
        )
        proposal = reasoning_agent.decide(context)
        return {
            "decision_proposal": {
                "action": proposal.action,
                "subject_id": proposal.subject_id,
                "thesis": proposal.thesis,
                "rationale": proposal.rationale,
                "evidence_refs": list(proposal.evidence_refs),
                "risks": list(proposal.risks),
                "opportunity_cost": proposal.opportunity_cost,
                "capital_impact": proposal.capital_impact,
                "confidence": proposal.confidence,
                "invalidation_conditions": list(proposal.invalidation_conditions),
                "as_of": proposal.as_of.isoformat() if proposal.as_of else None,
            }
        }

    def validate(state: B3State) -> dict[str, Any]:
        proposal = state["decision_proposal"]
        from b3_agent.schemas.decision import DecisionProposal

        decision = DecisionProposal(
            action=proposal["action"],
            subject_id=proposal["subject_id"],
            thesis=proposal["thesis"],
            rationale=proposal["rationale"],
            evidence_refs=tuple(proposal["evidence_refs"]),
            risks=tuple(proposal["risks"]),
            opportunity_cost=proposal["opportunity_cost"],
            capital_impact=proposal["capital_impact"],
            confidence=proposal["confidence"],
            invalidation_conditions=tuple(proposal["invalidation_conditions"]),
        )
        result = risk_validator.validate(decision)
        return {
            "risk_validation": {
                "status": result.status,
                "reasons": list(result.reasons),
            },
            "status": result.status,
        }

    graph = StateGraph(B3State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("reason", reason)
    graph.add_node("validate", validate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "validate")
    graph.add_edge("validate", END)
    return graph.compile()
