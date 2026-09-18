import pytest

from b3_agent.knowledge.graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from b3_agent.knowledge.graph_store import KnowledgeGraphStore
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore


def make_graph():
    company = GraphEntity("COMP-PETROBRAS", EntityType.COMPANY, "Petrobras", canonical_id="PETROBRAS")
    stock = GraphEntity("STK-PETR4", EntityType.STOCK, "PETR4", canonical_id="PETR4")
    option = GraphEntity("OPT-PETRI32", EntityType.OPTION, "PETRI32", canonical_id="PETRI32")
    sector = GraphEntity("SEC-OIL-GAS", EntityType.SECTOR, "Oil & Gas")
    ticker = GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id)
    underlying = GraphRelation(option.entity_id, RelationType.UNDERLYING, stock.entity_id)
    sector_edge = GraphRelation(stock.entity_id, RelationType.BELONGS_TO, sector.entity_id)
    return company, stock, option, sector, ticker, underlying, sector_edge


def test_implements_store_contract_and_supports_batch_upsert():
    store = InMemoryKnowledgeGraphStore()
    assert isinstance(store, KnowledgeGraphStore)
    company, stock, option, sector, ticker, underlying, sector_edge = make_graph()

    store.upsert([company, stock, option, sector], [ticker, underlying, sector_edge])

    assert store.count_entities() == 4
    assert store.count_entities(entity_type=EntityType.STOCK) == 1
    assert store.count_relations() == 3
    assert store.get_entity("STK-PETR4") == stock


def test_relation_upsert_is_idempotent_and_replaces_edge():
    store = InMemoryKnowledgeGraphStore()
    company, stock, *_rest = make_graph()
    store.upsert_entity(company)
    store.upsert_entity(stock)

    first = GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id, properties={"source": "b3"})
    second = GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id, properties={"source": "validated"})
    store.upsert_relation(first)
    store.upsert_relation(second)

    assert store.count_relations() == 1
    assert store.get_relations()[0] == second


def test_relation_requires_existing_and_compatible_endpoints():
    store = InMemoryKnowledgeGraphStore()
    company, stock, option, *_ = make_graph()
    store.upsert_entity(company)

    with pytest.raises(ValueError, match="endpoints must already exist"):
        store.upsert_relation(GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id))

    store.upsert_entity(stock)
    store.upsert_entity(option)
    with pytest.raises(ValueError, match="invalid source type"):
        store.upsert_relation(GraphRelation(stock.entity_id, RelationType.UNDERLYING, option.entity_id))


def test_structured_filters_and_neighbors_are_directional_and_unique():
    store = InMemoryKnowledgeGraphStore()
    company, stock, option, sector, ticker, underlying, sector_edge = make_graph()
    store.upsert([company, stock, option, sector], [ticker, underlying, sector_edge])

    assert store.find_entities(canonical_id="PETR4") == [stock]
    assert store.find_entities(name="Oil & Gas") == [sector]
    assert store.get_relations(target_id=stock.entity_id, relation=RelationType.UNDERLYING) == [underlying]
    assert store.neighbors(stock.entity_id, direction="out") == [sector]
    assert store.neighbors(stock.entity_id, direction="in") == [company, option]
    assert store.neighbors(stock.entity_id, direction="both") == [sector, company, option]
    assert store.neighbors(stock.entity_id, direction="in", limit=1) == [company]


def test_invalid_direction_and_limit_are_rejected():
    store = InMemoryKnowledgeGraphStore()
    with pytest.raises(ValueError, match="direction"):
        store.neighbors("missing", direction="sideways")
    with pytest.raises(ValueError, match="limit"):
        store.find_entities(limit=0)
    with pytest.raises(ValueError, match="limit"):
        store.get_relations(limit=-1)


def test_delete_entity_cascades_attached_relations():
    store = InMemoryKnowledgeGraphStore()
    company, stock, option, sector, ticker, underlying, sector_edge = make_graph()
    store.upsert([company, stock, option, sector], [ticker, underlying, sector_edge])

    store.delete_entity(stock.entity_id)

    assert store.get_entity(stock.entity_id) is None
    assert store.count_entities() == 3
    assert store.count_relations() == 0


def test_delete_relation_uses_relation_identity():
    store = InMemoryKnowledgeGraphStore()
    company, stock, *_rest = make_graph()
    store.upsert([company, stock], [])
    edge = GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id)
    store.upsert_relation(edge)

    store.delete_relation(GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id, properties={"ignored": True}))

    assert store.count_relations() == 0


def test_replacing_entity_preserves_relation_integrity():
    store = InMemoryKnowledgeGraphStore()
    company, stock, *_rest = make_graph()
    store.upsert([company, stock], [GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id)])

    replacement = GraphEntity("STK-PETR4", EntityType.STOCK, "PETR4 updated", canonical_id="PETR4")
    store.upsert_entity(replacement)

    assert store.get_entity(stock.entity_id) == replacement
    assert store.count_relations() == 1
