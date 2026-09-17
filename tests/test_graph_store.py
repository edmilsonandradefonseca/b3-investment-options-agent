from b3_agent.knowledge.graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from b3_agent.knowledge.graph_store import KnowledgeGraphStore


class MinimalGraphStore(KnowledgeGraphStore):
    def __init__(self):
        self.entities = {}
        self.relations = []

    def upsert_entity(self, entity):
        self.entities[entity.entity_id] = entity

    def upsert_relation(self, relation):
        self.relations.append(relation)

    def get_entity(self, entity_id):
        return self.entities.get(entity_id)

    def find_entities(self, *, entity_type=None, canonical_id=None, name=None, limit=100):
        values = list(self.entities.values())
        if entity_type is not None:
            values = [e for e in values if e.entity_type == entity_type]
        if canonical_id is not None:
            values = [e for e in values if e.canonical_id == canonical_id]
        if name is not None:
            values = [e for e in values if e.name == name]
        return values[:limit]

    def get_relations(self, *, source_id=None, relation=None, target_id=None, limit=100):
        values = self.relations
        if source_id is not None:
            values = [r for r in values if r.source_id == source_id]
        if relation is not None:
            values = [r for r in values if r.relation == relation]
        if target_id is not None:
            values = [r for r in values if r.target_id == target_id]
        return values[:limit]

    def neighbors(self, entity_id, *, relation=None, direction="both", limit=100):
        ids = []
        for r in self.relations:
            if relation is not None and r.relation != relation:
                continue
            if direction in ("both", "out") and r.source_id == entity_id:
                ids.append(r.target_id)
            if direction in ("both", "in") and r.target_id == entity_id:
                ids.append(r.source_id)
        return [self.entities[i] for i in ids[:limit] if i in self.entities]

    def delete_entity(self, entity_id):
        self.entities.pop(entity_id, None)
        self.relations = [r for r in self.relations if r.source_id != entity_id and r.target_id != entity_id]

    def delete_relation(self, relation):
        self.relations = [r for r in self.relations if r != relation]

    def count_entities(self, *, entity_type=None):
        return len(self.find_entities(entity_type=entity_type))

    def count_relations(self, *, relation=None):
        return len(self.get_relations(relation=relation))


def test_interface_supports_structured_graph_operations():
    store = MinimalGraphStore()
    stock = GraphEntity("STK-PETR4", EntityType.STOCK, "PETR4", canonical_id="PETR4")
    company = GraphEntity("COMP-PETROBRAS", EntityType.COMPANY, "Petrobras", canonical_id="PETROBRAS")
    relation = GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id)

    store.upsert(stock, [relation]) if False else store.upsert_entity(stock)
    store.upsert_entity(company)
    store.upsert_relation(relation)

    assert store.get_entity("STK-PETR4") == stock
    assert store.find_entities(entity_type=EntityType.STOCK)[0] == stock
    assert store.get_relations(source_id=company.entity_id)[0] == relation
    assert store.neighbors(company.entity_id, direction="out")[0] == stock


def test_default_batch_upsert_and_delete_contract():
    store = MinimalGraphStore()
    stock = GraphEntity("STK-PETR4", EntityType.STOCK, "PETR4")
    company = GraphEntity("COMP-PETROBRAS", EntityType.COMPANY, "Petrobras")
    relation = GraphRelation(company.entity_id, RelationType.TICKER, stock.entity_id)

    store.upsert([stock, company], [relation])
    assert store.count_entities() == 2
    assert store.count_relations() == 1

    store.delete_entity(company.entity_id)
    assert store.count_entities() == 1
    assert store.count_relations() == 0
