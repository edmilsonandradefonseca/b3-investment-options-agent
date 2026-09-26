from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from .graph_store import KnowledgeGraphStore


class Neo4jKnowledgeGraphStore(KnowledgeGraphStore):
    """Concrete Neo4j adapter behind the provider-neutral KnowledgeGraphStore boundary."""

    def __init__(self, driver, *, database: str | None = None) -> None:
        self.driver = driver
        self.database = database
        self._ensure_constraints()

    def _session(self):
        if self.database:
            return self.driver.session(database=self.database)
        return self.driver.session()

    def _ensure_constraints(self) -> None:
        with self._session() as session:
            session.run(
                "CREATE CONSTRAINT b3_entity_id IF NOT EXISTS "
                "FOR (n:B3Entity) REQUIRE n.entity_id IS UNIQUE"
            )

    def upsert_entity(self, entity: GraphEntity) -> None:
        payload = _entity_payload(entity)
        with self._session() as session:
            session.run(
                """
                MERGE (n:B3Entity {entity_id: $entity_id})
                SET n.entity_type = $entity_type,
                    n.name = $name,
                    n.canonical_id = $canonical_id,
                    n.properties_json = $properties_json,
                    n.source_ref = $source_ref,
                    n.provenance = $provenance,
                    n.as_of = $as_of,
                    n.valid_from = $valid_from,
                    n.valid_to = $valid_to
                """,
                **payload,
            )

    def upsert_relation(self, relation: GraphRelation) -> None:
        relation_type = relation.relation.value.upper()
        if not relation_type.replace("_", "").isalnum():
            raise ValueError("invalid relation type")
        payload = _relation_payload(relation)
        with self._session() as session:
            session.run(
                f"""
                MATCH (s:B3Entity {{entity_id: $source_id}})
                MATCH (t:B3Entity {{entity_id: $target_id}})
                MERGE (s)-[r:{relation_type}]->(t)
                SET r.properties_json = $properties_json,
                    r.source_ref = $source_ref,
                    r.provenance = $provenance,
                    r.as_of = $as_of,
                    r.valid_from = $valid_from,
                    r.valid_to = $valid_to
                """,
                **payload,
            )

    def get_entity(self, entity_id: str) -> GraphEntity | None:
        with self._session() as session:
            record = session.run(
                """
                MATCH (n:B3Entity {entity_id: $entity_id})
                RETURN n.entity_id AS entity_id,
                       n.entity_type AS entity_type,
                       n.name AS name,
                       n.canonical_id AS canonical_id,
                       n.properties_json AS properties_json,
                       n.source_ref AS source_ref,
                       n.provenance AS provenance,
                       n.as_of AS as_of,
                       n.valid_from AS valid_from,
                       n.valid_to AS valid_to
                """,
                entity_id=entity_id,
            ).single()
        return _entity_from_record(record) if record else None

    def find_entities(
        self,
        *,
        entity_type: EntityType | None = None,
        canonical_id: str | None = None,
        name: str | None = None,
        limit: int = 100,
    ) -> list[GraphEntity]:
        _validate_limit(limit)
        clauses = []
        params: dict[str, Any] = {"limit": limit}
        if entity_type is not None:
            clauses.append("n.entity_type = $entity_type")
            params["entity_type"] = entity_type.value
        if canonical_id is not None:
            clauses.append("n.canonical_id = $canonical_id")
            params["canonical_id"] = canonical_id
        if name is not None:
            clauses.append("n.name = $name")
            params["name"] = name
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._session() as session:
            rows = session.run(
                f"""
                MATCH (n:B3Entity)
                {where}
                RETURN n.entity_id AS entity_id,
                       n.entity_type AS entity_type,
                       n.name AS name,
                       n.canonical_id AS canonical_id,
                       n.properties_json AS properties_json,
                       n.source_ref AS source_ref,
                       n.provenance AS provenance,
                       n.as_of AS as_of,
                       n.valid_from AS valid_from,
                       n.valid_to AS valid_to
                ORDER BY n.entity_id
                LIMIT $limit
                """,
                **params,
            )
            return [_entity_from_record(row) for row in rows]

    def get_relations(
        self,
        *,
        source_id: str | None = None,
        relation: RelationType | None = None,
        target_id: str | None = None,
        limit: int = 100,
    ) -> list[GraphRelation]:
        _validate_limit(limit)
        clauses = []
        params: dict[str, Any] = {"limit": limit}
        if source_id is not None:
            clauses.append("s.entity_id = $source_id")
            params["source_id"] = source_id
        if target_id is not None:
            clauses.append("t.entity_id = $target_id")
            params["target_id"] = target_id
        if relation is not None:
            clauses.append("type(r) = $relation")
            params["relation"] = relation.value.upper()
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._session() as session:
            rows = session.run(
                f"""
                MATCH (s:B3Entity)-[r]->(t:B3Entity)
                {where}
                RETURN s.entity_id AS source_id,
                       toLower(type(r)) AS relation,
                       t.entity_id AS target_id,
                       r.properties_json AS properties_json,
                       r.source_ref AS source_ref,
                       r.provenance AS provenance,
                       r.as_of AS as_of,
                       r.valid_from AS valid_from,
                       r.valid_to AS valid_to
                ORDER BY source_id, relation, target_id
                LIMIT $limit
                """,
                **params,
            )
            return [_relation_from_record(row) for row in rows]

    def neighbors(
        self,
        entity_id: str,
        *,
        relation: RelationType | None = None,
        direction: str = "both",
        limit: int = 100,
    ) -> list[GraphEntity]:
        _validate_limit(limit)
        if direction not in {"in", "out", "both"}:
            raise ValueError("direction must be one of: in, out, both")

        candidate_ids: list[str] = []
        if direction in {"out", "both"}:
            candidate_ids.extend(
                item.target_id
                for item in self.get_relations(
                    source_id=entity_id,
                    relation=relation,
                    limit=limit,
                )
            )
        if direction in {"in", "both"}:
            candidate_ids.extend(
                item.source_id
                for item in self.get_relations(
                    target_id=entity_id,
                    relation=relation,
                    limit=limit,
                )
            )

        output: list[GraphEntity] = []
        seen: set[str] = set()
        for candidate_id in candidate_ids:
            if candidate_id in seen:
                continue
            entity = self.get_entity(candidate_id)
            if entity is not None:
                seen.add(candidate_id)
                output.append(entity)
            if len(output) >= limit:
                break
        return output

    def delete_entity(self, entity_id: str) -> None:
        with self._session() as session:
            session.run(
                "MATCH (n:B3Entity {entity_id: $entity_id}) DETACH DELETE n",
                entity_id=entity_id,
            )

    def delete_relation(self, relation: GraphRelation) -> None:
        relation_type = relation.relation.value.upper()
        with self._session() as session:
            session.run(
                f"""
                MATCH (s:B3Entity {{entity_id: $source_id}})
                      -[r:{relation_type}]->
                      (t:B3Entity {{entity_id: $target_id}})
                DELETE r
                """,
                source_id=relation.source_id,
                target_id=relation.target_id,
            )

    def count_entities(self, *, entity_type: EntityType | None = None) -> int:
        params: dict[str, Any] = {}
        where = ""
        if entity_type is not None:
            where = "WHERE n.entity_type = $entity_type"
            params["entity_type"] = entity_type.value
        with self._session() as session:
            record = session.run(
                f"MATCH (n:B3Entity) {where} RETURN count(n) AS count",
                **params,
            ).single()
        return int(record["count"]) if record else 0

    def count_relations(self, *, relation: RelationType | None = None) -> int:
        params: dict[str, Any] = {}
        where = ""
        if relation is not None:
            where = "WHERE type(r) = $relation"
            params["relation"] = relation.value.upper()
        with self._session() as session:
            record = session.run(
                f"MATCH (:B3Entity)-[r]->(:B3Entity) {where} RETURN count(r) AS count",
                **params,
            ).single()
        return int(record["count"]) if record else 0


def _validate_limit(limit: int) -> None:
    if limit <= 0:
        raise ValueError("limit must be greater than zero")


def _entity_payload(entity: GraphEntity) -> dict[str, Any]:
    return {
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "canonical_id": entity.canonical_id,
        "properties_json": json.dumps(entity.properties, sort_keys=True, default=str),
        "source_ref": entity.source_ref,
        "provenance": entity.provenance,
        "as_of": _iso(entity.as_of),
        "valid_from": _iso(entity.valid_from),
        "valid_to": _iso(entity.valid_to),
    }


def _relation_payload(relation: GraphRelation) -> dict[str, Any]:
    return {
        "source_id": relation.source_id,
        "target_id": relation.target_id,
        "properties_json": json.dumps(relation.properties, sort_keys=True, default=str),
        "source_ref": relation.source_ref,
        "provenance": relation.provenance,
        "as_of": _iso(relation.as_of),
        "valid_from": _iso(relation.valid_from),
        "valid_to": _iso(relation.valid_to),
    }


def _entity_from_record(record) -> GraphEntity:
    return GraphEntity(
        entity_id=record["entity_id"],
        entity_type=EntityType(record["entity_type"]),
        name=record["name"],
        canonical_id=record["canonical_id"],
        properties=json.loads(record["properties_json"] or "{}"),
        source_ref=record["source_ref"],
        provenance=record["provenance"],
        as_of=_dt(record["as_of"]),
        valid_from=_dt(record["valid_from"]),
        valid_to=_dt(record["valid_to"]),
    )


def _relation_from_record(record) -> GraphRelation:
    return GraphRelation(
        source_id=record["source_id"],
        relation=RelationType(record["relation"]),
        target_id=record["target_id"],
        properties=json.loads(record["properties_json"] or "{}"),
        source_ref=record["source_ref"],
        provenance=record["provenance"],
        as_of=_dt(record["as_of"]),
        valid_from=_dt(record["valid_from"]),
        valid_to=_dt(record["valid_to"]),
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None
