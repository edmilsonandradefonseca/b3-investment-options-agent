from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
from typing import Any

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.agents.specialist import MarketAnalysisAgent, OptionsAnalysisAgent, PortfolioAnalysisAgent
from b3_agent.agents.synthesis import SynthesisAgent
from b3_agent.config import settings
from b3_agent.knowledge.context import KnowledgeContextBuilder
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.indexer import KnowledgeIndexer
from b3_agent.knowledge.memory import ObsidianMemoryManager
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.llm.client import OpenAIResponsesClient
from b3_agent.schemas.position import PortfolioContext
from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.portfolio.context import PortfolioIntelligenceEngine
from langgraph.graph import END, START, StateGraph

from .contracts import B3State
from .orchestrator import configure_workflow
from .workflow import build_workflow


def configure_dashboard_workflow() -> None:
    """Compose the deterministic Dashboard path without requiring LLM/Obsidian."""
    snapshots = load_active_snapshots(settings.data_dir)

    def retrieve(state: B3State) -> dict[str, Any]:
        task = state.get("user_question") or state.get("request")
        if not task:
            raise ValueError("dashboard workflow requires user_question or request")
        return {"user_question": task}

    def snapshot(state: B3State) -> dict[str, Any]:
        return {
            "dashboard_snapshot": {
                "portfolio_context": state.get("portfolio_context"),
                "portfolio_intelligence": state.get("portfolio_intelligence"),
                "options_transactions": list(state.get("options_transactions", ())),
            },
            "status": "COMPLETED",
        }

    graph = StateGraph(B3State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("dashboard_snapshot", snapshot)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "dashboard_snapshot")
    graph.add_edge("dashboard_snapshot", END)
    workflow = graph.compile()

    def invoke(state: B3State) -> dict[str, Any]:
        initial = {**snapshots, **state}
        portfolio = initial.get("portfolio_context")
        if portfolio is not None:
            initial["portfolio_intelligence"] = asdict(PortfolioIntelligenceEngine().build(portfolio))
        return workflow.invoke(initial)

    configure_workflow(invoke)

def configure_default_workflow(*, vault_path: Path | None = None,
                                portfolio_context: PortfolioContext | dict[str, Any] | None = None,
                                opportunity_set: OpportunitySet | None = None) -> None:
    """Compose and register the production V3.1 workflow."""
    resolved_vault = Path(vault_path).expanduser().resolve() if vault_path is not None else settings.obsidian_vault
    if resolved_vault is None:
        raise RuntimeError("B3_AGENT_OBSIDIAN_VAULT is not configured; cannot compose the workflow")
    if not resolved_vault.is_dir():
        raise FileNotFoundError(f"Obsidian vault does not exist: {resolved_vault}")
    if not settings.llm_enabled:
        raise RuntimeError("B3_AGENT_LLM_ENABLED is false; cannot compose the reasoning workflow")

    llm = OpenAIResponsesClient(model=settings.llm_model)
    store = ObsidianKnowledgeStore(resolved_vault)
    retriever = ObsidianRetriever(store)
    graph = InMemoryKnowledgeGraphStore()
    KnowledgeIndexer(store, graph).index_all()
    knowledge_context_builder = KnowledgeContextBuilder(retriever, graph)
    memory_manager = ObsidianMemoryManager(store, retriever, graph)
    workflow = build_workflow(
        retriever=retriever,
        knowledge_context_builder=knowledge_context_builder,
        memory_manager=memory_manager,
        market_agent=MarketAnalysisAgent(llm),
        portfolio_agent=PortfolioAnalysisAgent(llm),
        options_agent=OptionsAnalysisAgent(llm),
        synthesis_agent=SynthesisAgent(llm),
        reasoning_agent=InvestmentReasoningAgent(llm),
        risk_validator=RiskValidator(),
    )

    deterministic_defaults: dict[str, Any] = load_active_snapshots(settings.data_dir)
    if portfolio_context is not None:
        deterministic_defaults["portfolio_context"] = portfolio_context
    if opportunity_set is not None:
        deterministic_defaults["opportunity_set"] = opportunity_set

    if deterministic_defaults:
        def invoke_with_deterministic_context(state):
            initial_state = {**deterministic_defaults, **state}
            return workflow.invoke(initial_state)
        configure_workflow(invoke_with_deterministic_context)
    else:
        configure_workflow(workflow)
