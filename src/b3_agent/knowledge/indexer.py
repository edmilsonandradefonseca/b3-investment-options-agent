from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
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
    notes_unchanged: int = 0
    notes_changed: int = 0
    notes_removed: int = 0
    entities_removed: int = 0
    relations_removed: int = 0


class KnowledgeIndexer:
    """Index structured Obsidian metadata into the Knowledge Graph.

    The indexer is deliberately deterministic and LLM-free. A note becomes a
    graph entity only when its YAML front matter declares ``entity_type``.
    Relations are declared as ``relation.<name>: <target_entity_id>``. The
    indexer performs a two-pass scan so relations can point to entities declared
    in other notes.

    ``index_all()`` maintains a small JSON manifest inside the vault containing
    SHA-256 content hashes and the graph objects previously produced by each
    note. On subsequent calls, unchanged notes are skipped when their graph
    objects are still present; changed notes are reconciled; deleted notes have
    their previously indexed entities and relations removed.
    """

    _MANIFEST_PATH = Path("00_System") / "Knowledge" / ".index_manifest.json"

    def __init__(self, obsidian: ObsidianKnowledgeStore, graph: KnowledgeGraphStore) -> None:
        self.obsidian = obsidian
        self.graph = graph

    def index_all(self) -> KnowledgeIndexResult:
        """Incrementally scan Markdown notes and reconcile graph state."""
        notes = self.obsidian.list_notes()
        current = {str(path): self.obsidian.read_note(path) for path in notes}
        previous = self._load_manifest()

        removed_paths = sorted(set(previous) - set(current))
        changed_paths: list[str] = []
        unchanged_paths: list[str] = []

        for path, content in current.items():
            content_hash = _content_hash(content)
            entry = previous.get(path)
            if entry and entry.get("content_hash") == content_hash and self._entry_present(entry):
                unchanged_paths.append(path)
            else:
                changed_paths.append(path)

        removed_entities = 0
        removed_relations = 0
        for path in removed_paths:
            counts = self._remove_manifest_entry(previous[path])
            removed_entities += counts[0]
            removed_relations += counts[1]

        parsed: dict[str, dict[str, Any]] = {
            path: self.parse_front_matter(content) for path, content in current.items()
        }

        # Reconcile changed notes before creating current entities. This removes
        # stale relations and entities while preserving unchanged graph objects.
        for path in changed_paths:
            old_entry = previous.get(path)
            if old_entry:
                counts = self._remove_manifest_entry(old_entry)
                removed_entities += counts[0]
                removed_relations += counts[1]

        entities: dict[str, GraphEntity] = {}
        relations: dict[str, list[GraphRelation]] = {}
        for path in changed_paths:
            entity = self._entity_from_metadata(Path(path), parsed[path])
            if entity is None:
                continue
            entities[path] = entity
            relations[path] = self._relations_from_metadata(entity, parsed[path])

        # Entities are written first, allowing cross-note relations to resolve.
        for entity in entities.values():
            self.graph.upsert_entity(entity)

        relation_count = 0
        for relation_list in relations.values():
            for relation in relation_list:
                self.graph.upsert_relation(relation)
                relation_count += 1

        manifest: dict[str, dict[str, Any]] = {}
        for path, content in current.items():
            if path in changed_paths:
                entity = entities.get(path)
                relation_list = relations.get(path, [])
                manifest[path] = self._manifest_entry(content, entity, relation_list)
            else:
                manifest[path] = previous[path]

        self._write_manifest(manifest)

        notes_without_entity = sum(
            1 for path in current if path in changed_paths and path not in entities
        ) + sum(
            1 for path in unchanged_paths if not previous[path].get("entity_ids")
        )
        return KnowledgeIndexResult(
            notes_scanned=len(notes),
            entities_indexed=len(entities),
            relations_indexed=relation_count,
            notes_without_entity=notes_without_entity,
            notes_unchanged=len(unchanged_paths),
            notes_changed=len(changed_paths),
            notes_removed=len(removed_paths),
            entities_removed=removed_entities,
            relations_removed=removed_relations,
        )

    def index_note(self, relative_path: str | Path) -> KnowledgeIndexResult:
        """Index one note and its declared entity/relations without manifest reconciliation."""
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

    def _entry_present(self, entry: dict[str, Any]) -> bool:
        entity_ids = [str(item) for item in entry.get("entity_ids", [])]
        for entity_id in entity_ids:
            entity = self.graph.get_entity(entity_id)
            if entity is None:
                return False
            if entity.source_ref != entry.get("source_ref"):
                return False

        for item in entry.get("relations", []):
            try:
                relation = GraphRelation(
                    source_id=str(item["source_id"]),
                    relation=RelationType(str(item["relation"])),
                    target_id=str(item["target_id"]),
                )
            except (KeyError, ValueError):
                return False
            matches = self.graph.get_relations(
                source_id=relation.source_id,
                relation=relation.relation,
                target_id=relation.target_id,
                limit=1,
            )
            if not matches:
                return False
        return True

    def _remove_manifest_entry(self, entry: dict[str, Any]) -> tuple[int, int]:
        relation_items = entry.get("relations", [])
        removed_relations = 0
        for item in relation_items:
            try:
                relation = GraphRelation(
                    source_id=str(item["source_id"]),
                    relation=RelationType(str(item["relation"])),
                    target_id=str(item["target_id"]),
                )
            except (KeyError, ValueError):
                continue
            if self.graph.get_relations(
                source_id=relation.source_id,
                relation=relation.relation,
                target_id=relation.target_id,
                limit=1,
            ):
                self.graph.delete_relation(relation)
                removed_relations += 1

        removed_entities = 0
        for entity_id in entry.get("entity_ids", []):
            entity = self.graph.get_entity(str(entity_id))
            if entity is not None and entity.source_ref == entry.get("source_ref"):
                self.graph.delete_entity(str(entity_id))
                removed_entities += 1
        return removed_entities, removed_relations

    @staticmethod
    def _manifest_entry(
        content: str,
        entity: GraphEntity | None,
        relations: list[GraphRelation],
    ) -> dict[str, Any]:
        return {
            "content_hash": _content_hash(content),
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "source_ref": entity.source_ref if entity is not None else None,
            "entity_ids": [entity.entity_id] if entity is not None else [],
            "relations": [
                {
                    "source_id": relation.source_id,
                    "relation": relation.relation.value,
                    "target_id": relation.target_id,
                }
                for relation in relations
            ],
        }

    def _load_manifest(self) -> dict[str, dict[str, Any]]:
        try:
            content = self.obsidian.read_note(self._MANIFEST_PATH)
        except FileNotFoundError:
            return {}
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid knowledge index manifest") from exc
        if not isinstance(data, dict) or not isinstance(data.get("notes", {}), dict):
            raise ValueError("invalid knowledge index manifest structure")
        return dict(data["notes"])

    def _write_manifest(self, manifest: dict[str, dict[str, Any]]) -> None:
        payload = {
            "version": 1,
            "notes": manifest,
        }
        self.obsidian.write_note(
            self._MANIFEST_PATH,
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )

    @staticmethod
    def parse_front_matter(content: str) -> dict[str, Any]:
        """Parse the simple scalar/list YAML subset used by the KG metadata."""
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


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
