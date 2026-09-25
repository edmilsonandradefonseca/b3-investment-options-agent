from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .b3_retriever import B3Retriever
from .graph_schema import EntityType, GraphEntity
from .neo4j_store import Neo4jKnowledgeGraphStore
from .sqlite_store import B3KnowledgeStore


class B3MemoryManager:
    """
    B3-native memory manager.

    Replaces the former ObsidianMemoryManager while preserving
    the interface expected by the LangGraph workflow.
    """

    def __init__(
        self,
        store: B3KnowledgeStore,
        retriever: B3Retriever,
        graph: Neo4jKnowledgeGraphStore,
    ) -> None:
        self.store = store
        self.retriever = retriever
        self.graph = graph

    def retrieve_context(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> dict[str, list[dict[str, Any]]]:
        records = self.retriever.retrieve(query, top_k=top_k)

        evidence = [
            {
                "source_ref": item.source_ref,
                "relative_path": item.relative_path,
                "snippet": item.snippet,
                "score": item.score,
            }
            for item in records
        ]

        return {
            "memory_context": evidence,
            "rag_context": evidence,
        }

    def persist_insight(
        self,
        insight: dict[str, Any],
    ) -> str:
        now = datetime.now(timezone.utc)

        insight_id = str(
            insight.get("insight_id")
            or f"INS-{now.strftime('%Y%m%d%H%M%S%f')}"
        )

        entity = str(insight.get("entity") or "UNKNOWN")
        title = str(insight.get("title") or "Investment insight")
        statement = str(insight.get("statement") or "")
        source = str(insight.get("source") or "B3 Investment Synthesis Agent")

        content = json.dumps(
            {
                "type": "insight",
                "insight_id": insight_id,
                "entity": entity,
                "title": title,
                "statement": statement,
                "evidence_refs": insight.get("evidence_refs", []),
                "source": source,
                "confidence": insight.get("confidence"),
                "created_at": now.isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )

        record = self._record(
            knowledge_id=insight_id,
            topic=entity,
            category="insight",
            content=content,
            evidence=statement,
            source=source,
            now=now,
        )

        self.store.record_discovery(record)
        self.retriever.index_record(record)

        entity_id = f"INSIGHT:{insight_id}"

        graph_entity = GraphEntity(
            entity_id=entity_id,
            entity_type=EntityType.INSIGHT,
            name=title,
            canonical_id=insight_id,
            properties={
                "entity": entity,
                "statement": statement,
                "confidence": insight.get("confidence"),
            },
            source_ref=source,
            provenance="b3_memory",
            as_of=now,
        )

        self.graph.upsert_entity(graph_entity)

        return f"b3://insights/{insight_id}"

    def persist_decision(
        self,
        decision: dict[str, Any],
        *,
        request: str,
        ticker: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)

        decision_id = str(
            decision.get("decision_id")
            or f"DEC-{now.strftime('%Y%m%d%H%M%S%f')}"
        )

        content = json.dumps(
            {
                "type": "decision",
                "decision_id": decision_id,
                "request": request,
                "ticker": ticker,
                "decision": decision,
                "created_at": now.isoformat(),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        record = self._record(
            knowledge_id=decision_id,
            topic=ticker or "portfolio",
            category="decision",
            content=content,
            evidence=request,
            source="B3 Investment Decision Context",
            now=now,
        )

        self.store.record_discovery(record)
        self.retriever.index_record(record)

        graph_entity = GraphEntity(
            entity_id=f"DECISION:{decision_id}",
            entity_type=EntityType.DECISION,
            name=f"Decision {decision_id}",
            canonical_id=decision_id,
            properties={
                "ticker": ticker,
                "request": request,
            },
            source_ref="b3_memory",
            provenance="b3_memory",
            as_of=now,
        )

        self.graph.upsert_entity(graph_entity)

        return f"b3://decisions/{decision_id}"

    @staticmethod
    def _record(
        *,
        knowledge_id: str,
        topic: str,
        category: str,
        content: str,
        evidence: str,
        source: str,
        now: datetime,
    ):
        from .models import KnowledgeRecord

        return KnowledgeRecord(
            knowledge_id=knowledge_id,
            topic=topic,
            category=category,
            status="active",
            version="1",
            created_at=now,
            updated_at=now,
            source=source,
            evidence=evidence,
            content=content,
        )
