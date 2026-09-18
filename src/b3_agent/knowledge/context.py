from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from .graph_store import KnowledgeGraphStore
from .retrieval import ObsidianRetriever, RetrievedEvidence


@dataclass(frozen=True)
class KnowledgeContext:
    """Bounded, unified context assembled from RAG, KG and deterministic data."""

    query: str
    as_of: datetime | None = None
    rag: tuple[RetrievedEvidence, ...] = ()
    entities: tuple[GraphEntity, ...] = ()
    relations: tuple[GraphRelation, ...] = ()
    events: tuple[GraphEntity, ...] = ()
    sources: tuple[str, ...] = ()
    freshness: tuple[dict[str, Any], ...] = ()
    confidence: tuple[dict[str, Any], ...] = ()
    deterministic_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return an agent/LLM-safe bounded representation."""
        return {
            "query": self.query,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "rag": [asdict(item) for item in self.rag],
            "entities": [_entity_dict(item) for item in self.entities],
            "relations": [_relation_dict(item) for item in self.relations],
            "events": [_entity_dict(item) for item in self.events],
            "sources": list(self.sources),
            "freshness": [dict(item) for item in self.freshness],
            "confidence": [dict(item) for item in self.confidence],
            "deterministic_context": dict(self.deterministic_context),
            "metadata": dict(self.metadata),
        }

    @property
    def evidence(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in self.rag]

    @property
    def graph_context(self) -> list[dict[str, Any]]:
        return (
            [{"type": "entity", **_entity_dict(item)} for item in self.entities]
            + [{"type": "relation", **_relation_dict(item)} for item in self.relations]
        )


class KnowledgeContextBuilder:
    """Combine bounded RAG, PIT-valid KG traversal and deterministic context."""

    def __init__(self, retriever: ObsidianRetriever, graph: KnowledgeGraphStore) -> None:
        self.retriever = retriever
        self.graph = graph

    def build(
        self,
        query: str,
        *,
        rag_top_k: int = 5,
        graph_top_k: int = 20,
        neighbor_depth: int = 1,
        as_of: datetime | None = None,
        deterministic_context: dict[str, Any] | None = None,
    ) -> KnowledgeContext:
        if not query.strip():
            raise ValueError("query must not be empty")
        if rag_top_k < 1 or graph_top_k < 1:
            raise ValueError("retrieval limits must be positive")
        if neighbor_depth < 0:
            raise ValueError("neighbor_depth must not be negative")
        if as_of is not None and as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        rag = self.retriever.retrieve(query, top_k=rag_top_k)
        seeds = self._seed_entities(query, rag, graph_top_k, as_of=as_of)
        entities, relations = self._expand(seeds, graph_top_k, neighbor_depth, as_of=as_of)
        events = tuple(item for item in entities if item.entity_type == EntityType.MARKET_EVENT)

        sources: list[str] = []
        for item in rag:
            if item.source_ref not in sources:
                sources.append(item.source_ref)
        for item in entities:
            if item.source_ref and item.source_ref not in sources:
                sources.append(item.source_ref)
        for item in relations:
            if item.source_ref and item.source_ref not in sources:
                sources.append(item.source_ref)

        return KnowledgeContext(
            query=query.strip(),
            as_of=as_of,
            rag=rag,
            entities=tuple(entities),
            relations=tuple(relations),
            events=events,
            sources=tuple(sources),
            deterministic_context=dict(deterministic_context or {}),
            metadata={
                "rag_count": len(rag),
                "entity_count": len(entities),
                "relation_count": len(relations),
                "event_count": len(events),
                "seed_count": len(seeds),
                "neighbor_depth": neighbor_depth,
                "point_in_time": as_of is not None,
            },
        )

    @staticmethod
    def _valid_at(item: GraphEntity | GraphRelation, as_of: datetime | None) -> bool:
        if as_of is None:
            return True
        if item.as_of is not None and item.as_of > as_of:
            return False
        if item.valid_from is not None and item.valid_from > as_of:
            return False
        if item.valid_to is not None and item.valid_to < as_of:
            return False
        return True

    def _seed_entities(
        self,
        query: str,
        rag: tuple[RetrievedEvidence, ...],
        limit: int,
        *,
        as_of: datetime | None = None,
    ) -> list[GraphEntity]:
        """Resolve graph identities explicitly mentioned by query/RAG text."""
        corpus = " ".join((query, *(item.snippet for item in rag))).casefold()
        candidates = self.graph.find_entities(limit=limit)
        scored: list[tuple[int, str, GraphEntity]] = []

        for entity in candidates:
            if not self._valid_at(entity, as_of):
                continue
            score = 0
            if entity.name and entity.name.casefold() in corpus:
                score += 3
            if entity.canonical_id and entity.canonical_id.casefold() in corpus:
                score += 5
            if score:
                scored.append((score, entity.entity_id, entity))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:limit]]

    def _expand(
        self,
        seeds: list[GraphEntity],
        limit: int,
        depth: int,
        *,
        as_of: datetime | None = None,
    ) -> tuple[list[GraphEntity], list[GraphRelation]]:
        entities: dict[str, GraphEntity] = {item.entity_id: item for item in seeds if self._valid_at(item, as_of)}
        relations: dict[tuple[str, RelationType, str], GraphRelation] = {}
        frontier = list(entities)

        for _ in range(depth + 1):
            next_frontier: list[str] = []
            for entity_id in frontier:
                edges = self.graph.get_relations(source_id=entity_id, limit=limit)
                edges += self.graph.get_relations(target_id=entity_id, limit=limit)
                for edge in edges:
                    if not self._valid_at(edge, as_of):
                        continue
                    key = (edge.source_id, edge.relation, edge.target_id)
                    relations[key] = edge
                    other_id = edge.target_id if edge.source_id == entity_id else edge.source_id
                    neighbor = self.graph.get_entity(other_id)
                    if neighbor is not None and self._valid_at(neighbor, as_of) and other_id not in entities:
                        entities[other_id] = neighbor
                        next_frontier.append(other_id)
                    if len(relations) >= limit:
                        break
                if len(relations) >= limit:
                    break
            frontier = next_frontier
            if not frontier or len(relations) >= limit:
                break

        ordered_entities = [entities[key] for key in sorted(entities)]
        ordered_relations = [relations[key] for key in sorted(relations, key=str)]
        return ordered_entities[:limit], ordered_relations[:limit]


def _entity_dict(entity: GraphEntity) -> dict[str, Any]:
    return {
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "canonical_id": entity.canonical_id,
        "properties": dict(entity.properties),
        "source_ref": entity.source_ref,
        "provenance": entity.provenance,
        "as_of": entity.as_of.isoformat() if entity.as_of else None,
        "valid_from": entity.valid_from.isoformat() if entity.valid_from else None,
        "valid_to": entity.valid_to.isoformat() if entity.valid_to else None,
    }


def _relation_dict(relation: GraphRelation) -> dict[str, Any]:
    return {
        "source_id": relation.source_id,
        "relation": relation.relation.value,
        "target_id": relation.target_id,
        "properties": dict(relation.properties),
        "source_ref": relation.source_ref,
        "provenance": relation.provenance,
        "as_of": relation.as_of.isoformat() if relation.as_of else None,
        "valid_from": relation.valid_from.isoformat() if relation.valid_from else None,
        "valid_to": relation.valid_to.isoformat() if relation.valid_to else None,
    }
