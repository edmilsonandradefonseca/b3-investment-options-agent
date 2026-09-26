from __future__ import annotations

from datetime import datetime, timezone
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
from b3_agent.agents.synthesis import SynthesisAgent
from b3_agent.knowledge.context import KnowledgeContextBuilder
from b3_agent.knowledge.memory import ObsidianMemoryManager
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.market_regime import MarketRegime

from .contracts import B3State
from .experience_workflow import ExperienceContextService
from .opportunity_context import opportunity_set_to_context


def build_workflow(
    *,
    reasoning_agent: InvestmentReasoningAgent,
    risk_validator: RiskValidator,
    retriever: ObsidianRetriever | None = None,
    memory_manager: ObsidianMemoryManager | None = None,
    knowledge_context_builder: KnowledgeContextBuilder | None = None,
    experience_context_service: ExperienceContextService | None = None,
    market_agent: MarketAnalysisAgent | None = None,
    portfolio_agent: PortfolioAnalysisAgent | None = None,
    options_agent: OptionsAnalysisAgent | None = None,
    synthesis_agent: SynthesisAgent | None = None,
):
    """Build the V4-compatible LangGraph workflow.

    Obsidian retriever/memory manager parameters remain legacy-compatible but are
    no longer required by the V4 target path.
    """

    def retrieve(state: B3State) -> dict[str, Any]:
        request = state.get("user_question") or state.get("request")
        if not request:
            raise ValueError("workflow requires user_question or request")
        return {"user_question": request}

    def deterministic_context(state: B3State) -> dict[str, Any]:
        opportunity_set = state.get("opportunity_set")
        if opportunity_set is None:
            return {
                "deterministic_context": dict(
                    state.get("deterministic_context", {})
                )
            }
        context = opportunity_set_to_context(opportunity_set)
        deterministic = {
            **state.get("deterministic_context", {}),
            "opportunity_set": context,
        }
        return {
            "opportunities": context["ranked_opportunities"],
            "action_candidates": context["action_candidates"],
            "deterministic_context": deterministic,
        }

    def experience_context(state: B3State) -> dict[str, Any]:
        if experience_context_service is None:
            return {}

        snapshot = state.get("feature_snapshot")
        regime = state.get("market_regime")
        if not isinstance(snapshot, FeatureSnapshot) or not isinstance(
            regime, MarketRegime
        ):
            return {}

        as_of = state.get("as_of")
        effective_as_of = (
            as_of if isinstance(as_of, datetime) else snapshot.as_of
        )
        if effective_as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        built = experience_context_service.build(
            query=state["user_question"],
            snapshot=snapshot,
            regime=regime,
            as_of=effective_as_of,
            ticker=state.get("ticker"),
            top_k=10,
        )
        return {
            "experience_retrieval": built.retrieval,
            "experience_assessment": built.assessment,
            "active_learnings": list(built.learnings),
            "historical_experiences": [
                match.reference_id
                for match in built.retrieval.matches
                if match.reference_type == "EXPERIENCE"
            ],
        }

    def knowledge_context(state: B3State) -> dict[str, Any]:
        """Build one bounded context containing evidence, graph and experience."""
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
                experience_retrieval=state.get("experience_retrieval"),
                experience_assessment=state.get("experience_assessment"),
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
            return {
                "memory_context": memory["memory_context"],
                "rag_context": memory["rag_context"],
                "evidence": evidence,
            }

        if retriever is not None:
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
            return {"evidence": evidence}

        return {"evidence": [], "sources": []}

    def _agent_context(state: B3State) -> AgentContext:
        keys = (
            "portfolio_context",
            "options_transactions",
            "signals",
            "threats",
            "opportunities",
            "action_candidates",
            "fundamental_analysis",
            "market_analysis",
            "options_analysis",
            "risk_analysis",
            "market_agent_analysis",
            "portfolio_agent_analysis",
            "options_agent_analysis",
            "synthesis",
            "knowledge_context",
            "memory_context",
            "rag_context",
            "graph_context",
            "experience_retrieval",
            "experience_assessment",
            "active_learnings",
            "historical_experiences",
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
        return {
            "market_agent_analysis": market_agent.analyze(
                _agent_context(state)
            ).to_dict()
        }

    def portfolio_analysis(state: B3State) -> dict[str, Any]:
        if portfolio_agent is None:
            return {}
        return {
            "portfolio_agent_analysis": portfolio_agent.analyze(
                _agent_context(state)
            ).to_dict()
        }

    def options_analysis(state: B3State) -> dict[str, Any]:
        if options_agent is None:
            return {}
        return {
            "options_agent_analysis": options_agent.analyze(
                _agent_context(state)
            ).to_dict()
        }

    def synthesis(state: B3State) -> dict[str, Any]:
        if synthesis_agent is None:
            return {}
        return {
            "synthesis": synthesis_agent.synthesize(_agent_context(state))
        }

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
        return {
            "decision_proposal": proposal_dict,
            "proposal": proposal_dict,
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
            invalidation_conditions=tuple(
                proposal["invalidation_conditions"]
            ),
        )
        result = risk_validator.validate(decision)
        return {
            "risk_validation": {
                "status": result.status,
                "reasons": list(result.reasons),
            },
            "status": result.status,
        }

    def persist_legacy_memory(state: B3State) -> dict[str, Any]:
        """Legacy-only Obsidian persistence; not part of the V4 target path."""
        if memory_manager is None:
            return {}

        persisted: list[str] = []
        ticker = state.get("ticker")
        synthesis_result = state.get("synthesis")
        if isinstance(synthesis_result, dict) and synthesis_result.get("summary"):
            entity = ticker or "PORTFOLIO"
            timestamp = datetime.now(timezone.utc).strftime(
                "%Y%m%d-%H%M%S-%f"
            )
            path = memory_manager.persist_insight(
                {
                    "insight_id": f"INS-{entity}-{timestamp}",
                    "entity": entity,
                    "type": "assessment",
                    "title": f"Investment assessment — {entity}",
                    "statement": synthesis_result["summary"],
                    "evidence_refs": synthesis_result.get(
                        "evidence_refs", []
                    ),
                    "source": "Investment Synthesis Agent",
                    "confidence": state.get(
                        "decision_proposal", {}
                    ).get("confidence"),
                }
            )
            persisted.append(path.as_posix())

        proposal = state.get("decision_proposal")
        if isinstance(proposal, dict):
            path = memory_manager.persist_decision(
                proposal,
                request=state["user_question"],
                ticker=ticker,
            )
            persisted.append(path.as_posix())

        return {
            "audit": [
                {
                    "event": "legacy_memory_persisted",
                    "paths": persisted,
                }
            ]
        }

    graph = StateGraph(B3State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("deterministic_context", deterministic_context)
    if experience_context_service is not None:
        graph.add_node("experience_context", experience_context)
    graph.add_node("knowledge_context", knowledge_context)
    graph.add_node("market_analysis", market_analysis)
    graph.add_node("portfolio_analysis", portfolio_analysis)
    graph.add_node("options_analysis", options_analysis)
    graph.add_node("reason", reason)
    graph.add_node("validate", validate)

    if memory_manager is not None:
        graph.add_node("persist_legacy_memory", persist_legacy_memory)
    if synthesis_agent is not None:
        graph.add_node("synthesis", synthesis)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "deterministic_context")
    if experience_context_service is not None:
        graph.add_edge("deterministic_context", "experience_context")
        graph.add_edge("experience_context", "knowledge_context")
    else:
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
        graph.add_edge("validate", "persist_legacy_memory")
        graph.add_edge("persist_legacy_memory", END)
    else:
        graph.add_edge("validate", END)

    return graph.compile()
