from pathlib import Path

from b3_agent.knowledge.graph_schema import EntityType, RelationType
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.memory import InsightRecord, ObsidianMemoryManager
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore


def test_persist_insight_mirrors_identity_and_relationships_in_kg(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    store = ObsidianKnowledgeStore(vault)
    graph = InMemoryKnowledgeGraphStore()

    from b3_agent.knowledge.graph_schema import GraphEntity

    stock = GraphEntity(
        entity_id="STK-ITUB4",
        entity_type=EntityType.STOCK,
        name="ITUB4",
        canonical_id="ITUB4",
        source_ref="04_Stocks/ITUB4.md",
    )
    graph.upsert_entity(stock)
    manager = ObsidianMemoryManager(store, graph=graph)

    path = manager.persist_insight(
        InsightRecord(
            insight_id="INS-20260917-001",
            entity="ITUB4",
            insight_type="risk",
            title="Portfolio concentration",
            statement="Concentration remains a material risk.",
            evidence=("obsidian:04_Stocks/ITUB4.md",),
            source="Risk Agent",
            confidence=0.8,
            previous_insight_id=None,
        )
    )

    assert path.exists()
    insight = graph.get_entity("INS-20260917-001")
    assert insight is not None
    assert insight.entity_type == EntityType.INSIGHT
    assert insight.source_ref == str(path)

    about = graph.get_relations(source_id="INS-20260917-001", relation=RelationType.ABOUT)
    assert len(about) == 1
    assert about[0].target_id == "STK-ITUB4"

    supported = graph.get_relations(source_id="INS-20260917-001", relation=RelationType.SUPPORTED_BY)
    assert len(supported) == 1
    evidence = graph.get_entity(supported[0].target_id)
    assert evidence is not None
    assert evidence.entity_type == EntityType.EVIDENCE
    assert evidence.canonical_id == "obsidian:04_Stocks/ITUB4.md"


def test_persist_insight_creates_supersedes_relationship(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    graph = InMemoryKnowledgeGraphStore()
    graph.upsert_entity(
        __import__("b3_agent.knowledge.graph_schema", fromlist=["GraphEntity"]).GraphEntity(
            entity_id="INS-OLD",
            entity_type=EntityType.INSIGHT,
            name="Old insight",
        )
    )
    manager = ObsidianMemoryManager(ObsidianKnowledgeStore(vault), graph=graph)

    manager.persist_insight(
        InsightRecord(
            insight_id="INS-NEW",
            entity=None,
            insight_type="assessment",
            title="Updated insight",
            statement="The updated assessment supersedes the prior one.",
            previous_insight_id="INS-OLD",
        )
    )

    edges = graph.get_relations(source_id="INS-NEW", relation=RelationType.SUPERSEDES)
    assert [(edge.source_id, edge.target_id) for edge in edges] == [("INS-NEW", "INS-OLD")]
