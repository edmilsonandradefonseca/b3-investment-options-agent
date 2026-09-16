from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from b3_agent.agents.context import AgentContext
from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.agents.specialist import (
    MarketAnalysisAgent,
    OptionsAnalysisAgent,
    PortfolioAnalysisAgent,
)
from b3_agent.knowledge.retrieval import ObsidianRetriever

from .contracts import B3State
from .opportunity_context import opportunity_set_to_context


def build_workflow(
    *,
    retriever: ObsidianRetriever,
    reasoning_agent: InvestmentReasoningAgent,
    risk_validator: RiskValidator,
    market_agent: MarketAnalysisAgent | None = None,
    portfolio_agent: PortfolioAnalysisAgent | None = None,
    options_agent: OptionsAnalysisAgent | None = None,
):
    """Build the LangGraph workflow behind the V3.1 orchestrator contract."""

    def retrieve(state: B3State) -> dict[str, Any]:
        request = state.get("user_question") or state.get("request")
        if not request:
            raise ValueError("workflow requires user_question or request")
        records = retriever.retrieve(request, top_k=5)
        evidence = [
            {
                "source_ref": item.source_ref,
                "relative_path": item.relative_path,
                "snippet": item.snippet,
                "score": item.score,
            }
            for item in records
        ]
        return {"user_question": request, "evidence": evidence}

    def deterministic_context(state: B3State) -> dict[str, Any]:
        opportunity_set = state.get("opportunity_set")
        if opportunity_set is None:
            return {}
        context = opportunity_set_to_context(opportunity_set)
        return {
            "opportunities": context["ranked_opportunities"],
            "action_candidates": context["action_candidates"],
            "deterministic_context": {"opportunity_set": context},
        }

    def _agent_context(state: B3State) -> AgentContext:
        keys = (
            "portfolio_context", "signals", "threats", "opportunities",
            "action_candidates", "fundamental_analysis", "market_analysis",
            "options_analysis", "risk_analysis",
        )
        facts = {key: state[key] for key in keys if key in state}
        legacy = state.get("deterministic_context")
        if isinstance(legacy, dict):
            facts = {**legacy, **facts}
        return AgentContext(
            request=state["user_question"],
            deterministic_context=facts,
            retrieved_evidence=tuple(state.get("evidence", [])),
        )

    def market_analysis(state: B3State) -> dict[str, Any]:
        if market_agent is None:
            return {}
        return {"market_analysis": market_agent.analyze(_agent_context(state)).to_dict()}

    def portfolio_analysis(state: B3State) -> dict[str, Any]:
        if portfolio_agent is None:
            return {}
        return {"portfolio_analysis": portfolio_agent.analyze(_agent_context(state)).to_dict()}

    def options_analysis(state: B3State) -> dict[str, Any]:
        if options_agent is None:
            return {}
        return {"options_analysis": options_agent.analyze(_agent_context(state)).to_dict()}

    def reason(state: B3State) -> dict[str, Any]:
        proposal = reasoning_agent.decide(_agent_context(state))
        proposal_dict = {
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
        return {"decision_proposal": proposal_dict, "proposal": proposal_dict}

    def validate(state: B3State) -> dict[str, Any]:
        proposal = state["decision_proposal"]
        from b3_agent.schemas.decision import DecisionProposal

        decision = DecisionProposal(
            action=proposal["action"], subject_id=proposal["subject_id"],
            thesis=proposal["thesis"], rationale=proposal["rationale"],
            evidence_refs=tuple(proposal["evidence_refs"]), risks=tuple(proposal["risks"]),
            opportunity_cost=proposal["opportunity_cost"], capital_impact=proposal["capital_impact"],
            confidence=proposal["confidence"], invalidation_conditions=tuple(proposal["invalidation_conditions"]),
        )
        result = risk_validator.validate(decision)
        return {"risk_validation": {"status": result.status, "reasons": list(result.reasons)}, "status": result.status}

    graph = StateGraph(B3State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("deterministic_context", deterministic_context)
    graph.add_node("market_analysis", market_analysis)
    graph.add_node("portfolio_analysis", portfolio_analysis)
    graph.add_node("options_analysis", options_analysis)
    graph.add_node("reason", reason)
    graph.add_node("validate", validate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "deterministic_context")
    graph.add_edge("deterministic_context", "market_analysis")
    graph.add_edge("market_analysis", "portfolio_analysis")
    graph.add_edge("portfolio_analysis", "options_analysis")
    graph.add_edge("options_analysis", "reason")
    graph.add_edge("reason", "validate")
    graph.add_edge("validate", END)
    return graph.compile()
