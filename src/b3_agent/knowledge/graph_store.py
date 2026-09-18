from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from .graph_schema import EntityType, GraphEntity, GraphRelation, RelationType


class KnowledgeGraphStore(ABC):
    """Storage boundary for the B3 Knowledge Graph.

    The interface deliberately contains no database-specific concepts. Concrete
    implementations may use an in-memory store, SQLite, Neo4j, or another
    backend without changing callers such as the indexer or LangGraph nodes.
    """

    @abstractmethod
    def upsert_entity(self, entity: GraphEntity) -> None:
        """Create or replace an entity using its canonical entity_id."""

    @abstractmethod
    def upsert_relation(self, relation: GraphRelation) -> None:
        """Create or replace a directed relation."""

    @abstractmethod
    def get_entity(self, entity_id: str) -> GraphEntity | None:
        """Return an entity by canonical identifier."""

    @abstractmethod
    def find_entities(
        self,
        *,
        entity_type: EntityType | None = None,
        canonical_id: str | None = None,
        name: str | None = None,
        limit: int = 100,
    ) -> list[GraphEntity]:
        """Find entities using structured filters."""

    @abstractmethod
    def get_relations(
        self,
        *,
        source_id: str | None = None,
        relation: RelationType | None = None,
        target_id: str | None = None,
        limit: int = 100,
    ) -> list[GraphRelation]:
        """Return relations matching structured endpoint/type filters."""

    @abstractmethod
    def neighbors(
        self,
        entity_id: str,
        *,
        relation: RelationType | None = None,
        direction: str = "both",
        limit: int = 100,
    ) -> list[GraphEntity]:
        """Return related entities in incoming, outgoing, or both directions."""

    @abstractmethod
    def delete_entity(self, entity_id: str) -> None:
        """Delete an entity and its directly attached relations."""

    @abstractmethod
    def delete_relation(self, relation: GraphRelation) -> None:
        """Delete a specific relation."""

    @abstractmethod
    def count_entities(self, *, entity_type: EntityType | None = None) -> int:
        """Return the number of stored entities."""

    @abstractmethod
    def count_relations(self, *, relation: RelationType | None = None) -> int:
        """Return the number of stored relations."""

    def upsert(self, entities: Iterable[GraphEntity], relations: Iterable[GraphRelation]) -> None:
        """Convenience operation for atomic-at-call-site graph ingestion.

        Implementations can override this when they support real transactions.
        The default preserves the interface's simple backend-neutral semantics.
        """
        entity_list = list(entities)
        relation_list = list(relations)
        for entity in entity_list:
            self.upsert_entity(entity)
        for relation in relation_list:
            self.upsert_relation(relation)

    def query(self, query: str, *, limit: int = 100) -> list[dict[str, Any]]:
        """Optional backend-specific query hook.

        Generic callers should prefer structured methods above. Implementations
        may expose a safe read-only query language, but this interface does not
        prescribe Cypher, SQL, Gremlin, or any other backend language.
        """
        raise NotImplementedError("free-form graph queries are backend-specific")
