from __future__ import annotations

from collections.abc import Iterable

from .graph_schema import EntityType, GraphEntity, GraphRelation, RelationType, validate_relation
from .graph_store import KnowledgeGraphStore


class InMemoryKnowledgeGraphStore(KnowledgeGraphStore):
    """Deterministic in-memory implementation of the KnowledgeGraphStore contract.

    This backend is intended for the MVP, indexing pipeline, tests, and local
    development. It deliberately provides no persistence or database-specific
    query language.
    """

    def __init__(self) -> None:
        self._entities: dict[str, GraphEntity] = {}
        self._relations: dict[tuple[str, RelationType, str], GraphRelation] = {}

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

    @staticmethod
    def _relation_key(relation: GraphRelation) -> tuple[str, RelationType, str]:
        return (relation.source_id, relation.relation, relation.target_id)

    def upsert_entity(self, entity: GraphEntity) -> None:
        """Create or replace an entity while preserving relation integrity."""
        for relation in self._relations.values():
            if relation.source_id == entity.entity_id:
                target = self._entities[relation.target_id]
                validate_relation(entity, relation, target)
            elif relation.target_id == entity.entity_id:
                source = self._entities[relation.source_id]
                validate_relation(source, relation, entity)
        self._entities[entity.entity_id] = entity

    def upsert_relation(self, relation: GraphRelation) -> None:
        """Create or replace a relation identified by source/type/target."""
        source = self._entities.get(relation.source_id)
        target = self._entities.get(relation.target_id)
        if source is None or target is None:
            raise ValueError("relation endpoints must already exist")
        validate_relation(source, relation, target)
        self._relations[self._relation_key(relation)] = relation

    def upsert(self, entities: Iterable[GraphEntity], relations: Iterable[GraphRelation]) -> None:
        """Upsert a batch using the same entity-then-relation semantics as the base contract."""
        for entity in entities:
            self.upsert_entity(entity)
        for relation in relations:
            self.upsert_relation(relation)

    def get_entity(self, entity_id: str) -> GraphEntity | None:
        return self._entities.get(entity_id)

    def find_entities(
        self,
        *,
        entity_type: EntityType | None = None,
        canonical_id: str | None = None,
        name: str | None = None,
        limit: int = 100,
    ) -> list[GraphEntity]:
        self._validate_limit(limit)
        values = self._entities.values()
        if entity_type is not None:
            values = (entity for entity in values if entity.entity_type == entity_type)
        if canonical_id is not None:
            values = (entity for entity in values if entity.canonical_id == canonical_id)
        if name is not None:
            values = (entity for entity in values if entity.name == name)
        return list(values)[:limit]

    def get_relations(
        self,
        *,
        source_id: str | None = None,
        relation: RelationType | None = None,
        target_id: str | None = None,
        limit: int = 100,
    ) -> list[GraphRelation]:
        self._validate_limit(limit)
        values = self._relations.values()
        if source_id is not None:
            values = (item for item in values if item.source_id == source_id)
        if relation is not None:
            values = (item for item in values if item.relation == relation)
        if target_id is not None:
            values = (item for item in values if item.target_id == target_id)
        return list(values)[:limit]

    def neighbors(
        self,
        entity_id: str,
        *,
        relation: RelationType | None = None,
        direction: str = "both",
        limit: int = 100,
    ) -> list[GraphEntity]:
        self._validate_limit(limit)
        if direction not in {"in", "out", "both"}:
            raise ValueError("direction must be one of: in, out, both")

        def collect(direction_filter: str) -> list[str]:
            ids: list[str] = []
            seen: set[str] = set()
            for edge in self._relations.values():
                if relation is not None and edge.relation != relation:
                    continue
                candidate: str | None = None
                if direction_filter == "out" and edge.source_id == entity_id:
                    candidate = edge.target_id
                elif direction_filter == "in" and edge.target_id == entity_id:
                    candidate = edge.source_id
                if candidate is not None and candidate not in seen:
                    seen.add(candidate)
                    ids.append(candidate)
            return ids

        if direction == "out":
            neighbor_ids = collect("out")[:limit]
        elif direction == "in":
            neighbor_ids = collect("in")[:limit]
        else:
            outbound = collect("out")
            inbound = [item for item in collect("in") if item not in set(outbound)]
            neighbor_ids = (outbound + inbound)[:limit]
        return [self._entities[item] for item in neighbor_ids]

    def delete_entity(self, entity_id: str) -> None:
        """Delete an entity and cascade-delete all attached relations."""
        self._entities.pop(entity_id, None)
        keys = [
            key
            for key, relation in self._relations.items()
            if relation.source_id == entity_id or relation.target_id == entity_id
        ]
        for key in keys:
            del self._relations[key]

    def delete_relation(self, relation: GraphRelation) -> None:
        self._relations.pop(self._relation_key(relation), None)

    def count_entities(self, *, entity_type: EntityType | None = None) -> int:
        if entity_type is None:
            return len(self._entities)
        return sum(entity.entity_type == entity_type for entity in self._entities.values())

    def count_relations(self, *, relation: RelationType | None = None) -> int:
        if relation is None:
            return len(self._relations)
        return sum(edge.relation == relation for edge in self._relations.values())
