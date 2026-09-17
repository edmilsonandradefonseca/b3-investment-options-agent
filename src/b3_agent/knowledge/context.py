from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .graph_schema import GraphEntity, GraphRelation, RelationType
from .graph_store import KnowledgeGraphStore
from .retrieval import ObsidianRetriever, RetrievedEvidence


@dataclass(frozen=True)
class KnowledgeContext:
    """Bounded, unified context assembled from RAG and the Knowledge Graph."""

    query: str
    rag: tuple[RetrievedEvidence, ...] = ()
    entities: tuple[GraphEntity, ...] = ()
    relations: tuple[GraphRelation, ...] = ()
    sources: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return an agent/LLM-safe bounded representation."""
        return {
            "query": self.query,
            "rag": [asdict(item) for item in self.rag],
            "entities": [_entity_dict(item) for item in self.entities],
            "relations": [_relation_dict(item) for item in self.relations],
            "sources": list(self.sources),
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
    """Combine bounded Obsidian retrieval with deterministic KG traversal."""

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
    ) -> KnowledgeContext:
        if not query.strip():
            raise ValueError("query must not be empty")
        if rag_top_k < 1 or graph_top_k < 1:
            raise ValueError("retrieval limits must be positive")
        if neighbor_depth < 0:
            raise ValueError("neighbor_depth must not be negative")

        rag = self.retriever.retrieve(query, top_k=rag_top_k)
        seeds = self._seed_entities(query, rag, graph_top_k)
        entities, relations = self._expand(seeds, graph_top_k, neighbor_depth)

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
            rag=rag,
            entities=tuple(entities),
            relations=tuple(relations),
            sources=tuple(sources),
            metadata={
                "rag_count": len(rag),
                "entity_count": len(entities),
                "relation_count": len(relations),
                "seed_count": len(seeds),
                "neighbor_depth": neighbor_depth,
            },
        )

    def _seed_entities(
        self,
        query: str,
        rag: tuple[RetrievedEvidence, ...],
        limit: int,
    ) -> list[GraphEntity]:
        """Resolve graph identities explicitly mentioned by query/RAG text."""
        corpus = " ".join((query, *(item.snippet for item in rag))).casefold()
        candidates = self.graph.find_entities(limit=limit)
        scored: list[tuple[int, str, GraphEntity]] = []

        for entity in candidates:
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
    ) -> tuple[list[GraphEntity], list[GraphRelation]]:
        entities: dict[str, GraphEntity] = {item.entity_id: item for item in seeds}
        relations: dict[tuple[str, RelationType, str], GraphRelation] = {}
        frontier = [item.entity_id for item in seeds]

        for _ in range(depth + 1):
            next_frontier: list[str] = []
            for entity_id in frontier:
                edges = self.graph.get_relations(source_id=entity_id, limit=limit)
                edges += self.graph.get_relations(target_id=entity_id, limit=limit)
                for edge in edges:
                    key = (edge.source_id, edge.relation, edge.target_id)
                    relations[key] = edge
                    other_id = edge.target_id if edge.source_id == entity_id else edge.source_id
                    neighbor = self.graph.get_entity(other_id)
                    if neighbor is not None and other_id not in entities:
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
