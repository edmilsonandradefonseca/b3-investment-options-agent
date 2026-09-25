from __future__ import annotations
import json

from typing import Any

from neo4j import GraphDatabase

from .graph_schema import EntityType, GraphEntity, GraphRelation, RelationType
from .graph_store import KnowledgeGraphStore


class Neo4jKnowledgeGraphStore(KnowledgeGraphStore):
    """Neo4j implementation of the backend-neutral KnowledgeGraphStore."""

    def __init__(
        self,
        uri: str = "bolt://127.0.0.1:7687",
        username: str = "neo4j",
        password: str | None = None,
        database: str = "neo4j",
    ) -> None:
        if not password:
            raise ValueError("Neo4j password is required")

        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self._driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
        )

    def connect(self) -> None:
        self._driver.verify_connectivity()

    def close(self) -> None:
        self._driver.close()

    def upsert_entity(self, entity: GraphEntity) -> None:
        query = """
        MERGE (e:Entity {entity_id: $entity_id})
        SET e.b3_namespace = true,
            e.entity_type = $entity_type,
            e.name = $name,
            e.canonical_id = $canonical_id,
            e.properties = $properties,
            e.source_ref = $source_ref,
            e.provenance = $provenance,
            e.as_of = $as_of,
            e.valid_from = $valid_from,
            e.valid_to = $valid_to
        """
        with self._driver.session(database=self.database) as session:
            session.run(
                query,
                entity_id=entity.entity_id,
                entity_type=entity.entity_type.value,
                name=entity.name,
                canonical_id=entity.canonical_id,
                properties=json.dumps(entity.properties, ensure_ascii=False),
                b3_namespace=True,
                source_ref=entity.source_ref,
                provenance=entity.provenance,
                as_of=entity.as_of.isoformat() if entity.as_of else None,
                valid_from=entity.valid_from.isoformat()
                if entity.valid_from else None,
                valid_to=entity.valid_to.isoformat()
                if entity.valid_to else None,
            ).consume()

    def upsert_relation(self, relation: GraphRelation) -> None:
        query = """
        MATCH (s:Entity {entity_id: $source_id})
        MATCH (t:Entity {entity_id: $target_id})
        MERGE (s)-[r:RELATION {relation_key: $relation_key}]->(t)
        SET r.relation = $relation,
            r.properties = $properties,
            r.source_ref = $source_ref,
            r.provenance = $provenance,
            r.as_of = $as_of,
            r.valid_from = $valid_from,
            r.valid_to = $valid_to
        """
        relation_key = (
            f"{relation.source_id}|"
            f"{relation.relation.value}|"
            f"{relation.target_id}"
        )

        with self._driver.session(database=self.database) as session:
            session.run(
                query,
                source_id=relation.source_id,
                target_id=relation.target_id,
                relation_key=relation_key,
                relation=relation.relation.value,
                properties=json.dumps(relation.properties, ensure_ascii=False),
                source_ref=relation.source_ref,
                provenance=relation.provenance,
                as_of=relation.as_of.isoformat() if relation.as_of else None,
                valid_from=relation.valid_from.isoformat()
                if relation.valid_from else None,
                valid_to=relation.valid_to.isoformat()
                if relation.valid_to else None,
            ).consume()

    def get_entity(self, entity_id: str) -> GraphEntity | None:
        query = """
        MATCH (e:Entity {entity_id: $entity_id})
        RETURN e
        """

        with self._driver.session(database=self.database) as session:
            record = session.run(query, entity_id=entity_id).single()

        return self._entity_from_node(record["e"]) if record else None

    def find_entities(
        self,
        *,
        entity_type: EntityType | None = None,
        canonical_id: str | None = None,
        name: str | None = None,
        limit: int = 100,
    ) -> list[GraphEntity]:
        conditions = []
        params: dict[str, Any] = {"limit": limit}

        if entity_type is not None:
            conditions.append("e.entity_type = $entity_type")
            params["entity_type"] = entity_type.value

        if canonical_id is not None:
            conditions.append("e.canonical_id = $canonical_id")
            params["canonical_id"] = canonical_id

        if name is not None:
            conditions.append("e.name = $name")
            params["name"] = name

        namespace_condition = "e.b3_namespace = true"
        if conditions:
            conditions.insert(0, namespace_condition)
        else:
            conditions.append(namespace_condition)

        where = f"WHERE {' AND '.join(conditions)}"

        query = f"""
        MATCH (e:Entity)
        {where}
        RETURN e
        ORDER BY e.entity_id
        LIMIT $limit
        """

        with self._driver.session(database=self.database) as session:
            records = session.run(query, **params)

            return [
                self._entity_from_node(record["e"])
                for record in records
            ]

    def get_relations(
        self,
        *,
        source_id: str | None = None,
        relation: RelationType | None = None,
        target_id: str | None = None,
        limit: int = 100,
    ) -> list[GraphRelation]:
        conditions = []
        params: dict[str, Any] = {"limit": limit}

        if source_id is not None:
            conditions.append("s.entity_id = $source_id")
            params["source_id"] = source_id

        if target_id is not None:
            conditions.append("t.entity_id = $target_id")
            params["target_id"] = target_id

        if relation is not None:
            conditions.append("r.relation = $relation")
            params["relation"] = relation.value

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
        MATCH (s:Entity)-[r:RELATION]->(t:Entity)
        {where}
        RETURN s.entity_id AS source_id,
               r.relation AS relation,
               t.entity_id AS target_id,
               r.properties AS properties,
               r.source_ref AS source_ref,
               r.provenance AS provenance,
               r.as_of AS as_of,
               r.valid_from AS valid_from,
               r.valid_to AS valid_to
        ORDER BY source_id, relation, target_id
        LIMIT $limit
        """

        with self._driver.session(database=self.database) as session:
            records = session.run(query, **params)

            return [
                GraphRelation(
                    source_id=record["source_id"],
                    relation=RelationType(record["relation"]),
                    target_id=record["target_id"],
                    properties=record["properties"] or {},
                    source_ref=record["source_ref"],
                    provenance=record["provenance"],
                    as_of=self._dt(record["as_of"]),
                    valid_from=self._dt(record["valid_from"]),
                    valid_to=self._dt(record["valid_to"]),
                )
                for record in records
            ]

    def neighbors(
        self,
        entity_id: str,
        *,
        relation: RelationType | None = None,
        direction: str = "both",
        limit: int = 100,
    ) -> list[GraphEntity]:
        if direction not in {"both", "out", "in"}:
            raise ValueError("direction must be both, out, or in")

        rel_filter = f"[r:RELATION {{relation: '{relation.value}'}}]" if relation else "[r:RELATION]"

        if direction == "out":
            pattern = f"(e:Entity)-{rel_filter}->(n:Entity)"
        elif direction == "in":
            pattern = f"(e:Entity)<-{rel_filter}-(n:Entity)"
        else:
            pattern = f"(e:Entity)-{rel_filter}-(n:Entity)"

        query = f"""
        MATCH {pattern}
        WHERE e.entity_id = $entity_id
        RETURN n
        ORDER BY n.entity_id
        LIMIT $limit
        """

        with self._driver.session(database=self.database) as session:
            records = session.run(
                query,
                entity_id=entity_id,
                limit=limit,
            )

            return [
                self._entity_from_node(record["n"])
                for record in records
            ]

    def delete_entity(self, entity_id: str) -> None:
        query = """
        MATCH (e:Entity {entity_id: $entity_id})
        DETACH DELETE e
        """

        with self._driver.session(database=self.database) as session:
            session.run(query, entity_id=entity_id).consume()

    def delete_relation(self, relation: GraphRelation) -> None:
        query = """
        MATCH (s:Entity {entity_id: $source_id})
              -[r:RELATION {relation: $relation}]
              ->(t:Entity {entity_id: $target_id})
        DELETE r
        """

        with self._driver.session(database=self.database) as session:
            session.run(
                query,
                source_id=relation.source_id,
                relation=relation.relation.value,
                target_id=relation.target_id,
            ).consume()

    def count_entities(self, *, entity_type: EntityType | None = None) -> int:
        if entity_type is None:
            query = "MATCH (e:Entity) RETURN count(e) AS count"
            params = {}
        else:
            query = """
            MATCH (e:Entity {entity_type: $entity_type})
            RETURN count(e) AS count
            """
            params = {"entity_type": entity_type.value}

        with self._driver.session(database=self.database) as session:
            return int(session.run(query, **params).single()["count"])

    def count_relations(self, *, relation: RelationType | None = None) -> int:
        if relation is None:
            query = "MATCH ()-[r:RELATION]->() RETURN count(r) AS count"
            params = {}
        else:
            query = """
            MATCH ()-[r:RELATION {relation: $relation}]->()
            RETURN count(r) AS count
            """
            params = {"relation": relation.value}

        with self._driver.session(database=self.database) as session:
            return int(session.run(query, **params).single()["count"])

    def query(self, query: str, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._driver.session(database=self.database) as session:
            records = session.run(query, limit=limit)
            return [record.data() for record in records]

    @staticmethod
    def _entity_from_node(node: Any) -> GraphEntity:
        return GraphEntity(
            entity_id=node["entity_id"],
            entity_type=EntityType(node["entity_type"]),
            name=node["name"],
            canonical_id=node["canonical_id"],
            properties=(
                json.loads(node["properties"])
                if isinstance(node.get("properties"), str)
                else (node.get("properties") or {})
            ),
            source_ref=node.get("source_ref"),
            provenance=node.get("provenance"),
            as_of=Neo4jKnowledgeGraphStore._dt(node.get("as_of")),
            valid_from=Neo4jKnowledgeGraphStore._dt(node.get("valid_from")),
            valid_to=Neo4jKnowledgeGraphStore._dt(node.get("valid_to")),
        )

    @staticmethod
    def _dt(value: str | None):
        if not value:
            return None

        from datetime import datetime

        return datetime.fromisoformat(value)
