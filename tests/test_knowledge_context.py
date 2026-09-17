from datetime import datetime, timezone
from pathlib import Path

import pytest

from b3_agent.knowledge.context import KnowledgeContextBuilder
from b3_agent.knowledge.graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever


AS_OF = datetime(2026, 9, 17, tzinfo=timezone.utc)


def _graph():
    company = GraphEntity("COMP-PETROBRAS", EntityType.COMPANY, "Petrobras", canonical_id="PETROBRAS", source_ref="obsidian:company.md")
    stock = GraphEntity("STK-PETR4", EntityType.STOCK, "PETR4", canonical_id="PETR4", source_ref="obsidian:petr4.md")
    option = GraphEntity("OPT-PETRI32", EntityType.OPTION, "PETRI32", canonical_id="PETRI32", source_ref="obsidian:petri32.md")
    sector = GraphEntity("SEC-OIL", EntityType.SECTOR, "Oil & Gas", source_ref="obsidian:sector.md")
    event = GraphEntity("EV-OIL", EntityType.MARKET_EVENT, "Oil market event", canonical_id="EV-OIL", source_ref="news:event.md", valid_from=AS_OF)
    future_stock = GraphEntity("STK-FUTURE", EntityType.STOCK, "PETR4 future", canonical_id="FUTURE", source_ref="future.md", valid_from=datetime(2026, 9, 18, tzinfo=timezone.utc))
    relations = [
        GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id, source_ref="obsidian:company.md"),
        GraphRelation(option.entity_id, RelationType.UNDERLYING, stock.entity_id, source_ref="obsidian:petri32.md"),
        GraphRelation(stock.entity_id, RelationType.BELONGS_TO, sector.entity_id, source_ref="obsidian:petr4.md"),
    ]
    return [company, stock, option, sector, event, future_stock], relations


def test_build_merges_rag_and_graph_without_unbounded_context(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "petr4.md").write_text("# PETR4\nPetrobras remains under review.\n", encoding="utf-8")
    (vault / "other.md").write_text("# Other\nUnrelated note.\n", encoding="utf-8")
    graph = InMemoryKnowledgeGraphStore()
    entities, relations = _graph()
    graph.upsert(entities, relations)
    context = KnowledgeContextBuilder(ObsidianRetriever(ObsidianKnowledgeStore(vault)), graph).build("PETR4", rag_top_k=1, graph_top_k=10, neighbor_depth=1)
    assert context.query == "PETR4"
    assert len(context.rag) == 1
    assert {item.entity_id for item in context.entities} == {"STK-PETR4", "COMP-PETROBRAS", "OPT-PETRI32", "SEC-OIL", "EV-OIL", "STK-FUTURE"}
    assert len(context.relations) == 3
    assert context.metadata["rag_count"] == 1
    assert context.metadata["entity_count"] == 6
    assert context.metadata["relation_count"] == 3
    assert context.sources[0].startswith("obsidian:")


def test_context_serialization_is_agent_safe(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "petr4.md").write_text("# PETR4\nPetrobras.\n", encoding="utf-8")
    graph = InMemoryKnowledgeGraphStore()
    entities, relations = _graph()
    graph.upsert(entities, relations)
    context = KnowledgeContextBuilder(ObsidianRetriever(ObsidianKnowledgeStore(vault)), graph).build(
        "PETR4", rag_top_k=1, graph_top_k=10, neighbor_depth=1, as_of=AS_OF,
        deterministic_context={"price_ref": "BRAPI:PETR4:2026-09-17", "options_ref": "OPLAB:PETR4"},
    )
    payload = context.as_dict()
    assert set(payload) == {"query", "as_of", "rag", "entities", "relations", "events", "sources", "freshness", "confidence", "deterministic_context", "metadata"}
    assert payload["as_of"] == AS_OF.isoformat()
    assert payload["entities"][0]["entity_type"] in {"company", "stock", "option", "sector"}
    assert isinstance(payload["relations"][0]["relation"], str)
    assert payload["deterministic_context"]["price_ref"].startswith("BRAPI:")
    assert [event["entity_id"] for event in payload["events"]] == ["EV-OIL"]


def test_point_in_time_filters_graph_entities_and_relations(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "petr4.md").write_text("# PETR4\n", encoding="utf-8")
    graph = InMemoryKnowledgeGraphStore()
    entities, relations = _graph()
    future_relation = GraphRelation("STK-PETR4", RelationType.RELATED_TO, "STK-FUTURE", source_ref="future.md", valid_from=datetime(2026, 9, 18, tzinfo=timezone.utc))
    graph.upsert(entities, [*relations, future_relation])
    context = KnowledgeContextBuilder(ObsidianRetriever(ObsidianKnowledgeStore(vault)), graph).build("PETR4", rag_top_k=1, graph_top_k=20, as_of=AS_OF)
    ids = {item.entity_id for item in context.entities}
    assert "STK-FUTURE" not in ids
    assert all(item.target_id != "STK-FUTURE" for item in context.relations)
    assert "EV-OIL" in ids
    assert context.metadata["point_in_time"] is True


def test_deterministic_context_is_optional_and_backward_compatible(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    graph = InMemoryKnowledgeGraphStore()
    context = KnowledgeContextBuilder(ObsidianRetriever(ObsidianKnowledgeStore(vault)), graph).build("PETR4")
    assert context.as_of is None
    assert context.events == ()
    assert context.deterministic_context == {}


def test_context_validation():
    graph = InMemoryKnowledgeGraphStore()
    retriever = ObsidianRetriever(ObsidianKnowledgeStore(Path(".")))
    builder = KnowledgeContextBuilder(retriever, graph)
    with pytest.raises(ValueError, match="query"): builder.build(" ")
    with pytest.raises(ValueError, match="positive"): builder.build("PETR4", rag_top_k=0)
    with pytest.raises(ValueError, match="positive"): builder.build("PETR4", graph_top_k=0)
    with pytest.raises(ValueError, match="negative"): builder.build("PETR4", neighbor_depth=-1)
    with pytest.raises(ValueError, match="timezone-aware"): builder.build("PETR4", as_of=datetime(2026, 9, 17))


def test_graph_only_context_is_allowed_when_rag_has_no_match(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "petr4.md").write_text("# PETR4\n", encoding="utf-8")
    graph = InMemoryKnowledgeGraphStore()
    entities, relations = _graph()
    graph.upsert(entities, relations)
    context = KnowledgeContextBuilder(ObsidianRetriever(ObsidianKnowledgeStore(vault)), graph).build("PETR4", rag_top_k=2, graph_top_k=10)
    assert context.entities
    assert context.relations


def test_langgraph_has_unified_knowledge_context_node(tmp_path: Path):
    from b3_agent.orchestration.workflow import build_workflow
    vault = tmp_path / "vault"
    vault.mkdir()
    retriever = ObsidianRetriever(ObsidianKnowledgeStore(vault))
    graph = InMemoryKnowledgeGraphStore()
    builder = KnowledgeContextBuilder(retriever, graph)
    workflow = build_workflow(retriever=retriever, knowledge_context_builder=builder, reasoning_agent=object(), risk_validator=object())
    assert "knowledge_context" in workflow.nodes
    assert "retrieve" in workflow.nodes
    assert "deterministic_context" in workflow.nodes
