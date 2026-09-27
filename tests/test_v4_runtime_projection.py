from __future__ import annotations

from datetime import date, datetime, timezone

from qdrant_client import QdrantClient

from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.knowledge.runtime_projection import RuntimeProjectionService
from b3_agent.research_events import ResearchEvent, ResearchSnapshot
from b3_agent.schemas.position import PortfolioContext, Position


def _service():
    graph = InMemoryKnowledgeGraphStore()
    embeddings = DeterministicEmbeddingProvider(dimensions=8)
    qdrant = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="runtime-projection-test",
        vector_size=8,
        hybrid=True,
    )
    return RuntimeProjectionService(
        graph=graph,
        vector_store=qdrant,
        embeddings=embeddings,
    ), graph, qdrant


def test_runtime_projection_projects_portfolio_graph():
    service, graph, _ = _service()
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 27),
        positions=(
            Position(
                position_id="btg:PETR4",
                ticker="PETR4",
                instrument_type="STOCK",
                quantity=100,
                market_price=30.0,
                market_value=3000.0,
                source_ref="BTG:Renda Variavel:Acoes",
            ),
        ),
        cash=0.0,
        cash_is_known=False,
        source_refs=("BTG:Renda Variavel",),
    )

    result = service.project_portfolio(portfolio)

    assert result["entities"] == 3
    assert result["relations"] == 2
    assert graph.count_entities() == 3
    assert graph.count_relations() == 2


def test_runtime_projection_projects_research_to_graph_and_qdrant():
    service, graph, qdrant = _service()
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
    snapshot = ResearchSnapshot(
        as_of=now,
        events=(
            ResearchEvent(
                event_id="https://example.com/petr4-news",
                ticker="PETR4",
                event_type="NEWS",
                published_at=now,
                available_at=now,
                headline="PETR4 market update",
                summary="Operational and market context for PETR4.",
                source_name="example",
                source_ref="https://example.com/petr4-news",
            ),
        ),
        excluded_future_count=0,
        source_refs=("https://example.com/petr4-news",),
    )

    result = service.project_research(snapshot)

    assert result["events"] == 1
    assert result["qdrant_chunks"] == 1
    assert qdrant.count() == 1
    assert graph.count_entities() == 2
    assert graph.count_relations() == 1
