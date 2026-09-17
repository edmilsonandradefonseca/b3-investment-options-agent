from pathlib import Path

import pytest

from b3_agent.knowledge.graph_schema import EntityType, RelationType
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.indexer import KnowledgeIndexer
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore


def write_note(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_index_all_builds_entities_and_cross_note_relations(tmp_path):
    write_note(tmp_path, "04_Stocks/PETR4.md", """---
entity_id: STK-PETR4
entity_type: stock
name: PETR4
canonical_id: PETR4
property.market: B3
relation.issued_by: COMP-PETROBRAS
relation.belongs_to: SEC-OIL-GAS
---
# PETR4
""")
    write_note(tmp_path, "04_Stocks/Petrobras.md", """---
entity_id: COMP-PETROBRAS
entity_type: company
name: Petrobras
canonical_id: PETROBRAS
---
""")
    write_note(tmp_path, "03_Research/OilGas.md", """---
entity_id: SEC-OIL-GAS
entity_type: sector
name: Oil & Gas
---
""")
    write_note(tmp_path, "README.md", "# Human-readable note without graph metadata\n")

    graph = InMemoryKnowledgeGraphStore()
    result = KnowledgeIndexer(ObsidianKnowledgeStore(tmp_path), graph).index_all()

    assert result.notes_scanned == 4
    assert result.entities_indexed == 3
    assert result.notes_without_entity == 1
    assert result.relations_indexed == 2
    assert result.notes_changed == 4
    assert graph.find_entities(entity_type=EntityType.STOCK)[0].canonical_id == "PETR4"
    assert graph.count_relations(relation=RelationType.ISSUED_BY) == 1
    assert graph.count_relations(relation=RelationType.BELONGS_TO) == 1


def test_index_all_is_idempotent_and_skips_unchanged_notes(tmp_path):
    write_note(tmp_path, "PETR4.md", """---
entity_id: STK-PETR4
entity_type: stock
name: PETR4
canonical_id: PETR4
---
""")
    graph = InMemoryKnowledgeGraphStore()
    indexer = KnowledgeIndexer(ObsidianKnowledgeStore(tmp_path), graph)

    first = indexer.index_all()
    second = indexer.index_all()

    assert first.entities_indexed == 1
    assert second.notes_unchanged == 1
    assert second.notes_changed == 0
    assert second.entities_indexed == 0
    assert graph.count_entities() == 1
    assert graph.count_relations() == 0


def test_incremental_index_reindexes_changed_note_and_replaces_relations(tmp_path):
    write_note(tmp_path, "PETR4.md", """---
entity_id: STK-PETR4
entity_type: stock
name: PETR4
canonical_id: PETR4
relation.belongs_to: SEC-OIL-GAS
---
""")
    write_note(tmp_path, "OilGas.md", """---
entity_id: SEC-OIL-GAS
entity_type: sector
name: Oil & Gas
---
""")
    write_note(tmp_path, "Banks.md", """---
entity_id: SEC-BANKS
entity_type: sector
name: Banks
---
""")
    graph = InMemoryKnowledgeGraphStore()
    indexer = KnowledgeIndexer(ObsidianKnowledgeStore(tmp_path), graph)
    indexer.index_all()

    write_note(tmp_path, "PETR4.md", """---
entity_id: STK-PETR4
entity_type: stock
name: PETR4
canonical_id: PETR4
relation.belongs_to: SEC-BANKS
---
""")
    result = indexer.index_all()

    assert result.notes_changed == 1
    assert result.notes_unchanged == 3
    assert result.relations_removed == 1
    assert graph.count_relations(relation=RelationType.BELONGS_TO) == 1
    edges = graph.get_relations(source_id="STK-PETR4", relation=RelationType.BELONGS_TO)
    assert edges[0].target_id == "SEC-BANKS"


def test_incremental_index_removes_deleted_note_and_its_graph_objects(tmp_path):
    write_note(tmp_path, "PETR4.md", """---
entity_id: STK-PETR4
entity_type: stock
name: PETR4
canonical_id: PETR4
relation.belongs_to: SEC-OIL-GAS
---
""")
    write_note(tmp_path, "OilGas.md", """---
entity_id: SEC-OIL-GAS
entity_type: sector
name: Oil & Gas
---
""")
    graph = InMemoryKnowledgeGraphStore()
    indexer = KnowledgeIndexer(ObsidianKnowledgeStore(tmp_path), graph)
    indexer.index_all()

    (tmp_path / "PETR4.md").unlink()
    result = indexer.index_all()

    assert result.notes_removed == 1
    assert result.entities_removed == 1
    assert result.relations_removed == 1
    assert graph.get_entity("STK-PETR4") is None
    assert graph.count_relations() == 0


def test_manifest_does_not_hide_missing_graph_objects(tmp_path):
    write_note(tmp_path, "PETR4.md", """---
entity_id: STK-PETR4
entity_type: stock
name: PETR4
canonical_id: PETR4
---
""")
    vault = ObsidianKnowledgeStore(tmp_path)
    first_graph = InMemoryKnowledgeGraphStore()
    KnowledgeIndexer(vault, first_graph).index_all()

    fresh_graph = InMemoryKnowledgeGraphStore()
    result = KnowledgeIndexer(vault, fresh_graph).index_all()

    assert result.notes_changed == 1
    assert result.notes_unchanged == 0
    assert fresh_graph.get_entity("STK-PETR4") is not None


def test_index_note_requires_relation_target_to_exist(tmp_path):
    write_note(tmp_path, "PETR4.md", """---
entity_id: STK-PETR4
entity_type: stock
name: PETR4
relation.issued_by: COMP-MISSING
---
""")
    graph = InMemoryKnowledgeGraphStore()

    with pytest.raises(ValueError, match="endpoints must already exist"):
        KnowledgeIndexer(ObsidianKnowledgeStore(tmp_path), graph).index_note("PETR4.md")


def test_front_matter_parser_is_small_and_deterministic():
    content = """---\nentity_id: STK-PETR4\nentity_type: stock\nname: \"PETR4\"\nproperty.price: 38.50\nproperty.active: true\nproperty.note: hello\n---\nBody\n"""
    metadata = KnowledgeIndexer.parse_front_matter(content)

    assert metadata["entity_id"] == "STK-PETR4"
    assert metadata["property.price"] == 38.50
    assert metadata["property.active"] is True
    assert metadata["property.note"] == "hello"


def test_invalid_metadata_is_rejected(tmp_path):
    write_note(tmp_path, "bad.md", "---\nentity_id: X\nentity_type: unknown\nname: X\n---\n")
    graph = InMemoryKnowledgeGraphStore()

    with pytest.raises(ValueError, match="invalid entity_type"):
        KnowledgeIndexer(ObsidianKnowledgeStore(tmp_path), graph).index_all()


def test_unstructured_markdown_is_not_forced_into_graph(tmp_path):
    write_note(tmp_path, "research.md", "# PETR4\nThis is narrative knowledge.\n")
    graph = InMemoryKnowledgeGraphStore()

    result = KnowledgeIndexer(ObsidianKnowledgeStore(tmp_path), graph).index_all()

    assert result.entities_indexed == 0
    assert graph.count_entities() == 0
