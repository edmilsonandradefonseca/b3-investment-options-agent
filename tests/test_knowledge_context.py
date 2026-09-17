from pathlib import Path

import pytest

from b3_agent.knowledge.context import KnowledgeContextBuilder
from b3_agent.knowledge.graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever


def _graph():
    company = GraphEntity("COMP-PETROBRAS", EntityType.COMPANY, "Petrobras", canonical_id="PETROBRAS", source_ref="obsidian:company.md")
    stock = GraphEntity("STK-PETR4", EntityType.STOCK, "PETR4", canonical_id="PETR4", source_ref="obsidian:petr4.md")
    option = GraphEntity("OPT-PETRI32", EntityType.OPTION, "PETRI32", canonical_id="PETRI32", source_ref="obsidian:petri32.md")
    sector = GraphEntity("SEC-OIL", EntityType.SECTOR, "Oil & Gas", source_ref="obsidian:sector.md")
    relations = [
        GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id, source_ref="obsidian:company.md"),
        GraphRelation(option.entity_id, RelationType.UNDERLYING, stock.entity_id, source_ref="obsidian:petri32.md"),
        GraphRelation(stock.entity_id, RelationType.BELONGS_TO, sector.entity_id, source_ref="obsidian:petr4.md"),
    ]
    return [company, stock, option, sector], relations


def test_build_merges_rag_and_graph_without_unbounded_context(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "petr4.md").write_text("# PETR4\nPetrobras remains under review.\n", encoding="utf-8")
    (vault / "other.md").write_text("# Other\nUnrelated note.\n", encoding="utf-8")

    graph = InMemoryKnowledgeGraphStore()
    entities, relations = _graph()
    graph.upsert(entities, relations)
    context = KnowledgeContextBuilder(ObsidianRetriever(ObsidianKnowledgeStore(vault)), graph).build(
        "PETR4", rag_top_k=1, graph_top_k=10, neighbor_depth=1
    )

    assert context.query == "PETR4"
    assert len(context.rag) == 1
    assert {item.entity_id for item in context.entities} == {
        "STK-PETR4", "COMP-PETROBRAS", "OPT-PETRI32", "SEC-OIL"
    }
    assert len(context.relations) == 3
    assert context.metadata["rag_count"] == 1
    assert context.metadata["entity_count"] == 4
    assert context.metadata["relation_count"] == 3
    assert context.sources[0].startswith("obsidian:")


def test_context_serialization_is_agent_safe():
    graph = InMemoryKnowledgeGraphStore()
    entities, relations = _graph()
    graph.upsert(entities, relations)
    context = KnowledgeContextBuilder(ObsidianRetriever(ObsidianKnowledgeStore(Path("."))), graph).build(
        "PETR4", rag_top_k=1, graph_top_k=10, neighbor_depth=1
    )

    payload = context.as_dict()
    assert set(payload) == {"query", "rag", "entities", "relations", "sources", "metadata"}
    assert payload["entities"][0]["entity_type"] in {"company", "stock", "option", "sector"}
    assert isinstance(payload["relations"][0]["relation"], str)


def test_context_validation():
    graph = InMemoryKnowledgeGraphStore()
    retriever = ObsidianRetriever(ObsidianKnowledgeStore(Path(".")))
    builder = KnowledgeContextBuilder(retriever, graph)

    with pytest.raises(ValueError, match="query"):
        builder.build(" ")
    with pytest.raises(ValueError, match="positive"):
        builder.build("PETR4", rag_top_k=0)
    with pytest.raises(ValueError, match="positive"):
        builder.build("PETR4", graph_top_k=0)
    with pytest.raises(ValueError, match="negative"):
        builder.build("PETR4", neighbor_depth=-1)


def test_graph_only_context_is_allowed_when_rag_has_no_match(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "petr4.md").write_text("# PETR4\n", encoding="utf-8")
    graph = InMemoryKnowledgeGraphStore()
    entities, relations = _graph()
    graph.upsert(entities, relations)

    context = KnowledgeContextBuilder(ObsidianRetriever(ObsidianKnowledgeStore(vault)), graph).build(
        "PETR4", rag_top_k=2, graph_top_k=10
    )
    assert context.entities
    assert context.relations
