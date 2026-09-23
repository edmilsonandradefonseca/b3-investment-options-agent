from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from b3_agent.agents.context import AgentContext
from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.agents.specialist import MarketAnalysisAgent, OptionsAnalysisAgent, PortfolioAnalysisAgent
from b3_agent.agents.synthesis import SynthesisAgent
from b3_agent.knowledge.context import KnowledgeContextBuilder
from b3_agent.knowledge.memory import ObsidianMemoryManager
from b3_agent.knowledge.retrieval import ObsidianRetriever

from .contracts import B3State
from .opportunity_context import opportunity_set_to_context


def build_workflow(*, retriever: ObsidianRetriever, reasoning_agent: InvestmentReasoningAgent,
                   risk_validator: RiskValidator, memory_manager: ObsidianMemoryManager | None = None,
                   knowledge_context_builder: KnowledgeContextBuilder | None = None,
                   market_agent: MarketAnalysisAgent | None = None,
                   portfolio_agent: PortfolioAnalysisAgent | None = None,
                   options_agent: OptionsAnalysisAgent | None = None,
                   synthesis_agent: SynthesisAgent | None = None):
    """Build the LangGraph workflow behind the V3.1 orchestrator contract."""

    def retrieve(state: B3State) -> dict[str, Any]:
        request = state.get("user_question") or state.get("request")
        if not request:
            raise ValueError("workflow requires user_question or request")
        return {"user_question": request}

    def dashboard_snapshot(state: B3State) -> dict[str, Any]:
        """Return deterministic dashboard data without invoking reasoning agents.

        The Dashboard is a client of the orchestrator contract. Snapshot reads
        are deliberately short-circuited before knowledge/LLM reasoning so a
        UI refresh cannot create an investment decision or memory side effect.
        """
        portfolio = state.get("portfolio_context")
        options = state.get("options_transactions", ())
        return {
            "dashboard_snapshot": {
                "portfolio_context": portfolio,
                "options_transactions": list(options),
            },
            "status": "COMPLETED",
        }

    def route_after_retrieve(state: B3State) -> str:
        return "dashboard_snapshot" if state.get("dashboard_view") else "deterministic_context"

    def deterministic_context(state: B3State) -> dict[str, Any]:
        opportunity_set = state.get("opportunity_set")
        if opportunity_set is None:
            return {"deterministic_context": dict(state.get("deterministic_context", {}))}
        context = opportunity_set_to_context(opportunity_set)
        deterministic = {**state.get("deterministic_context", {}), "opportunity_set": context}
        return {"opportunities": context["ranked_opportunities"], "action_candidates": context["action_candidates"], "deterministic_context": deterministic}

    def knowledge_context(state: B3State) -> dict[str, Any]:
        """Retrieve one bounded KnowledgeContext containing RAG, KG and deterministic context."""
        request = state["user_question"]
        if knowledge_context_builder is not None:
            as_of = state.get("as_of")
            if isinstance(as_of, datetime) and as_of.tzinfo is None:
                raise ValueError("as_of must be timezone-aware")
            context = knowledge_context_builder.build(
                request,
                rag_top_k=5,
                graph_top_k=20,
                neighbor_depth=1,
                as_of=as_of if isinstance(as_of, datetime) else None,
                deterministic_context=state.get("deterministic_context", {}),
            )
            return {
                "knowledge_context": context.as_dict(),
                "memory_context": context.evidence,
                "rag_context": context.evidence,
                "graph_context": context.graph_context,
                "evidence": context.evidence,
                "sources": list(context.sources),
            }
        if memory_manager is not None:
            memory = memory_manager.retrieve_context(request, top_k=5)
            evidence = list(memory["rag_context"])
            return {"memory_context": memory["memory_context"], "rag_context": memory["rag_context"], "evidence": evidence}
        records = retriever.retrieve(request, top_k=5)
        evidence = [{"source_ref": item.source_ref, "relative_path": item.relative_path, "snippet": item.snippet, "score": item.score} for item in records]
        return {"evidence": evidence}

    def _agent_context(state: B3State) -> AgentContext:
        keys = ("as_of", "portfolio_context", "portfolio_intelligence", "options_transactions", "options_performance", "signals", "threats", "opportunities", "action_candidates", "fundamental_analysis", "market_analysis", "options_analysis", "risk_analysis", "market_agent_analysis", "portfolio_agent_analysis", "options_agent_analysis", "synthesis", "knowledge_context", "memory_context", "rag_context", "graph_context")
        facts = {key: state[key] for key in keys if key in state}
        legacy = state.get("deterministic_context")
        if isinstance(legacy, dict): facts = {**legacy, **facts}
        return AgentContext(request=state["user_question"], deterministic_context=facts, retrieved_evidence=tuple(state.get("evidence", [])))

    def market_analysis(state: B3State) -> dict[str, Any]:
        if market_agent is None: return {}
        return {"market_agent_analysis": market_agent.analyze(_agent_context(state)).to_dict()}

    def portfolio_analysis(state: B3State) -> dict[str, Any]:
        if portfolio_agent is None: return {}
        return {"portfolio_agent_analysis": portfolio_agent.analyze(_agent_context(state)).to_dict()}

    def options_analysis(state: B3State) -> dict[str, Any]:
        if options_agent is None: return {}
        return {"options_agent_analysis": options_agent.analyze(_agent_context(state)).to_dict()}

    def synthesis(state: B3State) -> dict[str, Any]:
        if synthesis_agent is None: return {}
        return {"synthesis": synthesis_agent.synthesize(_agent_context(state))}

    def reason(state: B3State) -> dict[str, Any]:
        proposal = reasoning_agent.decide(_agent_context(state))
        proposal_dict = {"action": proposal.action, "subject_id": proposal.subject_id, "thesis": proposal.thesis, "rationale": proposal.rationale, "evidence_refs": list(proposal.evidence_refs), "risks": list(proposal.risks), "opportunity_cost": proposal.opportunity_cost, "capital_impact": proposal.capital_impact, "confidence": proposal.confidence, "invalidation_conditions": list(proposal.invalidation_conditions), "as_of": proposal.as_of.isoformat() if proposal.as_of else None}
        return {"decision_proposal": proposal_dict, "proposal": proposal_dict}

    def validate(state: B3State) -> dict[str, Any]:
        proposal = state["decision_proposal"]
        from b3_agent.schemas.decision import DecisionProposal
        decision = DecisionProposal(action=proposal["action"], subject_id=proposal["subject_id"], thesis=proposal["thesis"], rationale=proposal["rationale"], evidence_refs=tuple(proposal["evidence_refs"]), risks=tuple(proposal["risks"]), opportunity_cost=proposal["opportunity_cost"], capital_impact=proposal["capital_impact"], confidence=proposal["confidence"], invalidation_conditions=tuple(proposal["invalidation_conditions"]))
        result = risk_validator.validate(decision)
        return {"risk_validation": {"status": result.status, "reasons": list(result.reasons)}, "status": result.status}

    def persist_memory(state: B3State) -> dict[str, Any]:
        if memory_manager is None: return {}
        persisted: list[str] = []
        ticker = state.get("ticker")
        synthesis_result = state.get("synthesis")
        if isinstance(synthesis_result, dict) and synthesis_result.get("summary"):
            entity = ticker or "PORTFOLIO"
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            path = memory_manager.persist_insight({"insight_id": f"INS-{entity}-{timestamp}", "entity": entity, "type": "assessment", "title": f"Investment assessment — {entity}", "statement": synthesis_result["summary"], "evidence_refs": synthesis_result.get("evidence_refs", []), "source": "Investment Synthesis Agent", "confidence": state.get("decision_proposal", {}).get("confidence")})
            persisted.append(path.as_posix() if hasattr(path, "as_posix") else str(path))
        proposal = state.get("decision_proposal")
        if isinstance(proposal, dict):
            path = memory_manager.persist_decision(proposal, request=state["user_question"], ticker=ticker)
            persisted.append(path.as_posix() if hasattr(path, "as_posix") else str(path))
        return {"audit": [{"event": "memory_persisted", "paths": persisted}]}

    graph = StateGraph(B3State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("deterministic_context", deterministic_context)
    graph.add_node("knowledge_context", knowledge_context)
    graph.add_node("market_analysis", market_analysis)
    graph.add_node("portfolio_analysis", portfolio_analysis)
    graph.add_node("options_analysis", options_analysis)
    graph.add_node("reason", reason)
    graph.add_node("validate", validate)
    if memory_manager is not None: graph.add_node("persist_memory", persist_memory)
    if synthesis_agent is not None: graph.add_node("synthesis", synthesis)

    graph.add_node("dashboard_snapshot", dashboard_snapshot)
    graph.add_edge(START, "retrieve")
    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "dashboard_snapshot": "dashboard_snapshot",
            "deterministic_context": "deterministic_context",
        },
    )
    graph.add_edge("dashboard_snapshot", END)
    graph.add_edge("deterministic_context", "knowledge_context")
    graph.add_edge("knowledge_context", "market_analysis")
    graph.add_edge("knowledge_context", "portfolio_analysis")
    graph.add_edge("knowledge_context", "options_analysis")
    if synthesis_agent is not None:
        graph.add_edge("market_analysis", "synthesis")
        graph.add_edge("portfolio_analysis", "synthesis")
        graph.add_edge("options_analysis", "synthesis")
        graph.add_edge("synthesis", "reason")
    else:
        graph.add_edge("market_analysis", "reason")
        graph.add_edge("portfolio_analysis", "reason")
        graph.add_edge("options_analysis", "reason")
    graph.add_edge("reason", "validate")
    if memory_manager is not None:
        graph.add_edge("validate", "persist_memory")
        graph.add_edge("persist_memory", END)
    else: graph.add_edge("validate", END)
    return graph.compile()
