from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from b3_agent.agents.context import AgentContext
from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.knowledge.retrieval import ObsidianRetriever


class WorkflowState(TypedDict, total=False):
    request: str
    deterministic_context: dict[str, Any]
    evidence: list[dict[str, Any]]
    proposal: dict[str, Any]
    risk_validation: dict[str, Any]
    status: str


def build_workflow(
    *,
    retriever: ObsidianRetriever,
    reasoning_agent: InvestmentReasoningAgent,
    risk_validator: RiskValidator,
):
    """Build the MVP LangGraph orchestration without duplicating domain logic."""

    def retrieve(state: WorkflowState) -> dict[str, Any]:
        records = retriever.retrieve(state["request"], top_k=5)
        return {
            "evidence": [
                {
                    "source_ref": item.source_ref,
                    "relative_path": item.relative_path,
                    "snippet": item.snippet,
                    "score": item.score,
                }
                for item in records
            ]
        }

    def reason(state: WorkflowState) -> dict[str, Any]:
        context = AgentContext(
            request=state["request"],
            deterministic_context=state.get("deterministic_context", {}),
            retrieved_evidence=tuple(state.get("evidence", [])),
        )
        proposal = reasoning_agent.decide(context)
        return {
            "proposal": {
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

    def validate(state: WorkflowState) -> dict[str, Any]:
        proposal = state["proposal"]
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

    graph = StateGraph(WorkflowState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("reason", reason)
    graph.add_node("validate", validate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "validate")
    graph.add_edge("validate", END)
    return graph.compile()
