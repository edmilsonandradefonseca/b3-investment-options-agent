from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.agents.specialist import MarketAnalysisAgent, OptionsAnalysisAgent, PortfolioAnalysisAgent
from b3_agent.agents.synthesis import SynthesisAgent
from b3_agent.config import settings
from b3_agent.knowledge.context import KnowledgeContextBuilder
from b3_agent.knowledge.embeddings import HttpEmbeddingProvider
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.indexer import KnowledgeIndexer
from b3_agent.knowledge.memory import ObsidianMemoryManager
from b3_agent.knowledge.neo4j_store import Neo4jKnowledgeGraphStore
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.knowledge.retrieval import ObsidianRetriever, VectorEvidenceRetriever
from b3_agent.llm.client import OpenAIResponsesClient, OpenClawStructuredClient
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.schemas.position import PortfolioContext

from .orchestrator import configure_workflow
from .workflow import build_workflow
from .experience_workflow import ExperienceContextService
from b3_agent.intelligence.personal_history import PersonalHistoryService
from b3_agent.llm.reuse import ReusingLLMClient


B3_V4_QDRANT_COLLECTION = "b3_evidence_768_hybrid"
B3_V4_EMBEDDING_DIMENSIONS = 768


def _load_shared_env_value(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    env_path = Path(os.getenv("B3_SHARED_PLATFORM_ENV", "/opt/joao-runtime/joao.env"))
    if not env_path.is_file():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        if key.strip() == name:
            return raw.strip().strip('"').strip("'")
    return None


def _production_knowledge_context():
    embedding_url = os.getenv("B3_EMBEDDING_URL", "http://127.0.0.1:8093")
    qdrant_url = os.getenv("B3_QDRANT_URL", "http://127.0.0.1:6333")
    neo4j_uri = os.getenv("B3_NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_user = os.getenv("B3_NEO4J_USER", "neo4j")
    neo4j_password = _load_shared_env_value("NEO4J_PASSWORD")
    if not neo4j_password:
        raise RuntimeError("NEO4J_PASSWORD is not available in the environment or shared platform env")

    embeddings = HttpEmbeddingProvider(base_url=embedding_url, dimensions=B3_V4_EMBEDDING_DIMENSIONS)
    qdrant = QdrantVectorStore(
        client=QdrantClient(url=qdrant_url),
        collection_name=B3_V4_QDRANT_COLLECTION,
        vector_size=B3_V4_EMBEDDING_DIMENSIONS,
        hybrid=True,
    )
    retriever = VectorEvidenceRetriever(qdrant, embeddings)

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    driver.verify_connectivity()
    graph = Neo4jKnowledgeGraphStore(driver)
    return retriever, graph


def _legacy_test_context(vault_path: Path):
    resolved_vault = Path(vault_path).expanduser().resolve()
    if not resolved_vault.is_dir():
        raise FileNotFoundError(f"Obsidian vault does not exist: {resolved_vault}")
    store = ObsidianKnowledgeStore(resolved_vault)
    retriever = ObsidianRetriever(store)
    graph = InMemoryKnowledgeGraphStore()
    KnowledgeIndexer(store, graph).index_all()
    return retriever, graph, ObsidianMemoryManager(store, retriever, graph)


def _build_llm_client():
    provider = settings.llm_provider.strip().lower()

    if provider == "openclaw":
        return OpenClawStructuredClient(
            agent=settings.openclaw_agent,
            model=settings.openclaw_model,
            timeout=settings.openclaw_timeout_seconds,
            executable=settings.openclaw_bin,
        )

    if provider == "openai_api":
        if not settings.allow_openai_api_fallback:
            raise RuntimeError(
                "Direct OpenAI API fallback is disabled; set "
                "B3_ALLOW_OPENAI_API_FALLBACK=true to enable it explicitly"
            )
        return OpenAIResponsesClient(model=settings.llm_model)

    raise RuntimeError(
        f"Unsupported B3_AGENT_LLM_PROVIDER={settings.llm_provider!r}; "
        "expected 'openclaw' or 'openai_api'"
    )


def configure_default_workflow(
    *,
    vault_path: Path | None = None,
    portfolio_context: PortfolioContext | dict[str, Any] | None = None,
    opportunity_set: OpportunitySet | None = None,
    experience_context_service: ExperienceContextService | None = None,
) -> None:
    """Compose and register the V4 production workflow.

    Production defaults to the shared 768d embedding service, the B3-owned
    hybrid Qdrant collection and the Neo4j B3Entity namespace. Senior LLM
    reasoning defaults to the isolated OpenClaw b3-investment agent. Direct
    OpenAI API usage is an opt-in fallback only. vault_path is retained only
    for deterministic legacy tests and is not a production path.
    """
    if not settings.llm_enabled:
        raise RuntimeError("B3_AGENT_LLM_ENABLED is false; cannot compose the reasoning workflow")
    if experience_context_service is not None and not isinstance(experience_context_service, ExperienceContextService):
        raise TypeError("experience_context_service must be a trusted typed service")

    llm = ReusingLLMClient(_build_llm_client())
    memory_manager = None
    if vault_path is not None:
        retriever, graph, memory_manager = _legacy_test_context(vault_path)
    else:
        retriever, graph = _production_knowledge_context()

    knowledge_context_builder = KnowledgeContextBuilder(retriever, graph)
    workflow = build_workflow(
        retriever=retriever,
        knowledge_context_builder=knowledge_context_builder,
        memory_manager=memory_manager,
        personal_history_service=PersonalHistoryService(settings.data_dir),
        experience_context_service=experience_context_service,
        single_synthesis=os.getenv("B3_WORKSPACE_SINGLE_SYNTHESIS", "true").lower() == "true",
        market_agent=MarketAnalysisAgent(llm),
        portfolio_agent=PortfolioAnalysisAgent(llm),
        options_agent=OptionsAnalysisAgent(llm),
        synthesis_agent=SynthesisAgent(llm),
        reasoning_agent=InvestmentReasoningAgent(llm),
        risk_validator=RiskValidator(),
    )

    def invoke_with_deterministic_context(state):
        # Reload current portfolio on each invocation, not just runtime startup.
        defaults = load_active_snapshots(settings.data_dir)
        if portfolio_context is not None:
            defaults["portfolio_context"] = portfolio_context
        if opportunity_set is not None:
            defaults["opportunity_set"] = opportunity_set
        return workflow.invoke({**defaults, **state})
    configure_workflow(invoke_with_deterministic_context)
