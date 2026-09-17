from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from .graph_store import KnowledgeGraphStore
from .obsidian import ObsidianKnowledgeStore


@dataclass(frozen=True)
class KnowledgeIndexResult:
    """Deterministic summary of one indexing operation."""

    notes_scanned: int = 0
    entities_indexed: int = 0
    relations_indexed: int = 0
    notes_without_entity: int = 0


class KnowledgeIndexer:
    """Index structured Obsidian metadata into the Knowledge Graph.

    The indexer is deliberately deterministic and LLM-free. A note becomes a
    graph entity only when its YAML front matter declares ``entity_type``.
    Relations are declared as ``relation.<name>: <target_entity_id>``. The
    indexer performs a two-pass scan so relations can point to entities declared
    in other notes.

    Example:

        ---
        entity_id: STK-PETR4
        entity_type: stock
        name: PETR4
        canonical_id: PETR4
        ---

        relation.issued_by: COMP-PETROBRAS
    """

    def __init__(self, obsidian: ObsidianKnowledgeStore, graph: KnowledgeGraphStore) -> None:
        self.obsidian = obsidian
        self.graph = graph

    def index_all(self) -> KnowledgeIndexResult:
        """Scan every Markdown note and upsert all declared entities/relations."""
        notes = self.obsidian.list_notes()
        parsed: list[tuple[Path, dict[str, Any]]] = []
        for path in notes:
            parsed.append((path, self.parse_front_matter(self.obsidian.read_note(path))))

        entities: list[GraphEntity] = []
        for path, metadata in parsed:
            entity = self._entity_from_metadata(path, metadata)
            if entity is not None:
                entities.append(entity)

        # Entities are written first, allowing cross-note relations to resolve.
        for entity in entities:
            self.graph.upsert_entity(entity)

        relation_count = 0
        for path, metadata in parsed:
            entity = self._entity_from_metadata(path, metadata)
            if entity is None:
                continue
            for relation in self._relations_from_metadata(entity, metadata):
                self.graph.upsert_relation(relation)
                relation_count += 1

        return KnowledgeIndexResult(
            notes_scanned=len(notes),
            entities_indexed=len(entities),
            relations_indexed=relation_count,
            notes_without_entity=len(notes) - len(entities),
        )

    def index_note(self, relative_path: str | Path) -> KnowledgeIndexResult:
        """Index one note and its declared entity/relations."""
        path = Path(relative_path)
        metadata = self.parse_front_matter(self.obsidian.read_note(path))
        entity = self._entity_from_metadata(path, metadata)
        if entity is None:
            return KnowledgeIndexResult(notes_scanned=1, notes_without_entity=1)

        self.graph.upsert_entity(entity)
        relations = self._relations_from_metadata(entity, metadata)
        for relation in relations:
            self.graph.upsert_relation(relation)

        return KnowledgeIndexResult(
            notes_scanned=1,
            entities_indexed=1,
            relations_indexed=len(relations),
        )

    @staticmethod
    def parse_front_matter(content: str) -> dict[str, Any]:
        """Parse the simple scalar/list YAML subset used by the KG metadata.

        This avoids adding a YAML dependency to the MVP. Supported values are
        strings, numbers, booleans, null, and ``key: value`` pairs. Keys
        beginning with ``relation.`` declare graph relations.
        """
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}

        metadata: dict[str, Any] = {}
        end = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end = index
                break
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"Invalid front matter line: {line}")
            key, value = line.split(":", 1)
            key = key.strip()
            if not key:
                raise ValueError("front matter key must not be empty")
            metadata[key] = KnowledgeIndexer._parse_scalar(value.strip())

        if end is None:
            raise ValueError("front matter must be closed with ---")
        return metadata

    @staticmethod
    def _parse_scalar(value: str) -> Any:
        if not value:
            return ""
        if value.lower() in {"null", "none"}:
            return None
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return value

    @staticmethod
    def _entity_from_metadata(path: Path, metadata: dict[str, Any]) -> GraphEntity | None:
        if "entity_type" not in metadata:
            return None
        required = ("entity_id", "name")
        missing = [key for key in required if not str(metadata.get(key, "")).strip()]
        if missing:
            raise ValueError(f"missing entity metadata: {', '.join(missing)} ({path})")

        try:
            entity_type = EntityType(str(metadata["entity_type"]))
        except ValueError as exc:
            raise ValueError(f"invalid entity_type in {path}: {metadata['entity_type']}") from exc

        reserved = {"entity_id", "entity_type", "name", "canonical_id", "source_ref", "provenance", "as_of", "valid_from", "valid_to"}
        properties = {
            key.removeprefix("property."): value
            for key, value in metadata.items()
            if key.startswith("property.")
        }
        return GraphEntity(
            entity_id=str(metadata["entity_id"]),
            entity_type=entity_type,
            name=str(metadata["name"]),
            canonical_id=str(metadata["canonical_id"]) if metadata.get("canonical_id") is not None else None,
            properties=properties,
            source_ref=str(metadata["source_ref"]) if metadata.get("source_ref") is not None else str(path),
            provenance=str(metadata["provenance"]) if metadata.get("provenance") is not None else "obsidian",
        )

    @staticmethod
    def _relations_from_metadata(entity: GraphEntity, metadata: dict[str, Any]) -> list[GraphRelation]:
        relations: list[GraphRelation] = []
        for key, target_id in metadata.items():
            if not key.startswith("relation."):
                continue
            relation_name = key.removeprefix("relation.")
            try:
                relation_type = RelationType(relation_name)
            except ValueError as exc:
                raise ValueError(f"invalid relation type: {relation_name}") from exc
            if target_id is None or not str(target_id).strip():
                raise ValueError(f"relation target must not be empty: {key}")
            relations.append(
                GraphRelation(
                    source_id=entity.entity_id,
                    relation=relation_type,
                    target_id=str(target_id),
                    source_ref=entity.source_ref,
                    provenance="obsidian",
                )
            )
        return relations
