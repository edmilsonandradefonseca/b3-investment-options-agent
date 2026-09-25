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
from b3_agent.knowledge.b3_memory import B3MemoryManager
from b3_agent.knowledge.b3_retriever import B3Retriever
from b3_agent.knowledge.neo4j_store import Neo4jKnowledgeGraphStore
from b3_agent.knowledge.sqlite_store import B3KnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.llm.client import OpenAIResponsesClient
from b3_agent.schemas.position import PortfolioContext
from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.portfolio.context import PortfolioIntelligenceEngine
from b3_agent.options.performance import OptionPerformanceEngine
from b3_agent.options.reconciliation import OptionsReconciliationEngine, TransactionSourceCoverage
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.source_manifest import SourceManifestRepository
from b3_agent.schemas.option_transaction import OptionTransaction
from langgraph.graph import END, START, StateGraph

from .contracts import B3State
from .orchestrator import configure_workflow
from .workflow import build_workflow




def _build_options_reconciliation(data_dir: Path, portfolio: Any, raw_transactions: Any) -> dict[str, Any] | None:
    """Build auditable cross-source reconciliation without changing P&L inputs."""
    if not isinstance(portfolio, PortfolioContext):
        return None

    excel_transactions = tuple(
        OptionTransaction(**item) if isinstance(item, dict) else item
        for item in (raw_transactions or ())
    )
    ledger_path = Path(data_dir) / "options.sqlite3"
    brokerage_transactions = (
        OptionTransactionLedger(ledger_path).list_all()
        if ledger_path.is_file()
        else ()
    )
    transactions = excel_transactions + brokerage_transactions
    if not transactions:
        return None

    source_coverage: list[TransactionSourceCoverage] = []
    if excel_transactions:
        source_coverage.append(
            TransactionSourceCoverage(
                source_ref="Options Transactions XLSX",
                scope="PERIOD_ONLY",
                completeness="UNKNOWN",
            )
        )

    if brokerage_transactions:
        manifest_path = Path(data_dir) / "source_manifest.sqlite3"
        manifests = SourceManifestRepository(manifest_path).list_all() if manifest_path.is_file() else ()
        for manifest in manifests:
            matching_refs = {
                transaction.source_ref
                for transaction in brokerage_transactions
                if transaction.source_id == manifest.source_id
                or transaction.source_ref.startswith(manifest.source_ref)
            }
            for source_ref in sorted(matching_refs):
                source_coverage.append(
                    TransactionSourceCoverage(
                        source_ref=source_ref,
                        coverage_start=manifest.coverage_start,
                        coverage_end=manifest.coverage_end,
                        scope=manifest.scope,
                        completeness=manifest.completeness,
                    )
                )

    reconciliation = OptionsReconciliationEngine().reconcile(
        transactions,
        portfolio,
        source_coverage=tuple(source_coverage),
    )
    return asdict(reconciliation)


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
                "options_performance": state.get("options_performance", {"lifecycles": [], "by_underlying": []}),
                "options_transactions": list(state.get("options_transactions", ())),
                "options_reconciliation": state.get("options_reconciliation"),
                "opportunity_set": asdict(state["opportunity_set"]) if isinstance(state.get("opportunity_set"), OpportunitySet) else state.get("opportunity_set"),
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
        raw_transactions = initial.get("options_transactions", ())
        if raw_transactions:
            transactions = tuple(OptionTransaction(**item) if isinstance(item, dict) else item for item in raw_transactions)
            performances = OptionPerformanceEngine().build(transactions)
            aggregate = OptionPerformanceEngine().aggregate_by_underlying(performances)
            initial["options_performance"] = {
                "lifecycles": [asdict(item) for item in performances],
                "by_underlying": [asdict(item) for item in aggregate],
            }
        else:
            initial["options_performance"] = {"lifecycles": [], "by_underlying": []}
        initial["options_reconciliation"] = _build_options_reconciliation(
            settings.data_dir,
            initial.get("portfolio_context"),
            initial.get("options_transactions", ()),
        )
        return workflow.invoke(initial)

    configure_workflow(invoke)

def _apply_portfolio_capital_constraint(defaults: dict[str, Any]) -> dict[str, Any]:
    """Re-rank an upstream OpportunitySet against authoritative portfolio cash."""
    active_portfolio = defaults.get("portfolio_context")
    active_opportunity_set = defaults.get("opportunity_set")
    if not isinstance(active_opportunity_set, OpportunitySet):
        return defaults

    available_capital = None
    if isinstance(active_portfolio, PortfolioContext):
        available_capital = active_portfolio.cash
    elif isinstance(active_portfolio, dict):
        raw_cash = active_portfolio.get("cash")
        if isinstance(raw_cash, (int, float)):
            available_capital = float(raw_cash)

    if available_capital is None:
        return defaults

    ranked = []
    rejected = list(active_opportunity_set.rejected_opportunities)
    rejected_ids = {item.opportunity_id for item in rejected}
    capital_reason = None

    for assessment in active_opportunity_set.ranked_opportunities:
        if (
            available_capital is not None
            and assessment.capital_requirement is not None
            and assessment.capital_requirement > available_capital
        ):
            from dataclasses import replace

            capital_reason = (
                f"capital_requirement={assessment.capital_requirement} exceeds "
                f"available_capital={available_capital}"
            )
            rejected.append(
                replace(
                    assessment,
                    eligible=False,
                    rejection_reasons=tuple(
                        dict.fromkeys((*assessment.rejection_reasons, capital_reason))
                    ),
                )
            )
            rejected_ids.add(assessment.opportunity_id)
        else:
            ranked.append(assessment)

    if capital_reason is None:
        return defaults

    from dataclasses import replace

    affordable_ids = {item.opportunity_id for item in ranked}
    action_candidates = tuple(
        candidate
        for candidate in active_opportunity_set.action_candidates
        if not any(
            ref in rejected_ids
            for ref in candidate.opportunity_refs
        )
    )
    defaults["opportunity_set"] = replace(
        active_opportunity_set,
        ranked_opportunities=tuple(ranked),
        rejected_opportunities=tuple(rejected),
        action_candidates=action_candidates,
    )
    return defaults


def configure_default_workflow(*, vault_path: Path | None = None,
                                portfolio_context: PortfolioContext | dict[str, Any] | None = None,
                                opportunity_set: OpportunitySet | None = None) -> None:
    """Compose and register the production V3.1 workflow."""
    if not settings.llm_enabled:
        raise RuntimeError("B3_AGENT_LLM_ENABLED is false; cannot compose the reasoning workflow")

    llm = OpenAIResponsesClient(model=settings.llm_model)

    knowledge_store = B3KnowledgeStore(
        "/opt/b3-runtime/data/b3_knowledge.db"
    )

    retriever = B3Retriever(
        store=knowledge_store,
    )

    import os

    graph = Neo4jKnowledgeGraphStore(
        uri=os.getenv("B3_NEO4J_URI", "bolt://127.0.0.1:7687"),
        username=os.getenv("B3_NEO4J_USERNAME", "neo4j"),
        password=os.getenv("B3_NEO4J_PASSWORD"),
        database=os.getenv("B3_NEO4J_DATABASE", "neo4j"),
    )

    knowledge_context_builder = KnowledgeContextBuilder(
        retriever,
        graph,
    )

    memory_manager = B3MemoryManager(
        knowledge_store,
        retriever,
        graph,
    )
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

    # The conversational client must receive the same deterministic portfolio/options
    # facts as the Dashboard before any specialist/LLM reasoning. This keeps the
    # Copilot as a client of the existing intelligence workflow rather than a second
    # calculation engine.
    deterministic_defaults: dict[str, Any] = load_active_snapshots(settings.data_dir)
    if portfolio_context is not None:
        deterministic_defaults["portfolio_context"] = portfolio_context
    if opportunity_set is not None:
        deterministic_defaults["opportunity_set"] = opportunity_set

    active_portfolio = deterministic_defaults.get("portfolio_context")
    if isinstance(active_portfolio, PortfolioContext):
        deterministic_defaults["portfolio_intelligence"] = asdict(
            PortfolioIntelligenceEngine().build(active_portfolio)
        )
        if active_portfolio.as_of is not None:
            deterministic_defaults["as_of"] = active_portfolio.as_of
    elif isinstance(active_portfolio, dict):
        deterministic_defaults.setdefault(
            "portfolio_intelligence",
            active_portfolio.get("portfolio_intelligence", {}),
        )

    deterministic_defaults = _apply_portfolio_capital_constraint(deterministic_defaults)

    raw_transactions = deterministic_defaults.get("options_transactions", ())
    if raw_transactions:
        transactions = tuple(
            OptionTransaction(**item) if isinstance(item, dict) else item
            for item in raw_transactions
        )
        performances = OptionPerformanceEngine().build(transactions)
        deterministic_defaults["options_performance"] = {
            "lifecycles": [asdict(item) for item in performances],
            "by_underlying": [
                asdict(item)
                for item in OptionPerformanceEngine().aggregate_by_underlying(performances)
            ],
        }
    else:
        deterministic_defaults["options_performance"] = {
            "lifecycles": [],
            "by_underlying": [],
        }

    deterministic_defaults["options_reconciliation"] = _build_options_reconciliation(
        settings.data_dir,
        deterministic_defaults.get("portfolio_context"),
        deterministic_defaults.get("options_transactions", ()),
    )

    if deterministic_defaults:
        def invoke_with_deterministic_context(state):
            initial_state = {**deterministic_defaults, **state}
            return workflow.invoke(initial_state)
        configure_workflow(invoke_with_deterministic_context)
    else:
        configure_workflow(workflow)
