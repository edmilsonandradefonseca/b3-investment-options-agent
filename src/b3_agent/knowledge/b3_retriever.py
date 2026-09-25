from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid5, NAMESPACE_URL

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .models import KnowledgeRecord
from .sqlite_store import B3KnowledgeStore


MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_SIZE = 384
DEFAULT_COLLECTION = "b3_memory"
DEFAULT_QDRANT_URL = "http://127.0.0.1:6333"
DEFAULT_EMBEDDING_URL = "http://127.0.0.1:8093"


@dataclass(frozen=True)
class RetrievedEvidence:
    source_ref: str
    relative_path: str
    snippet: str
    score: float


class B3Retriever:
    def __init__(
        self,
        store: B3KnowledgeStore | None = None,
        qdrant_url: str = DEFAULT_QDRANT_URL,
        embedding_url: str = DEFAULT_EMBEDDING_URL,
        collection: str = DEFAULT_COLLECTION,
    ) -> None:
        self.store = store or B3KnowledgeStore()
        self.client = QdrantClient(url=qdrant_url)
        self.embedding_url = embedding_url.rstrip("/")
        self.collection = collection
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        names = {item.name for item in collections}

        if self.collection not in names:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )

    def _embed(self, text: str) -> list[float]:
        response = requests.post(
            f"{self.embedding_url}/embed",
            json={"text": text},
            timeout=60,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("dimensions") != VECTOR_SIZE:
            raise ValueError(
                f"Unexpected embedding dimensions: "
                f"{data.get('dimensions')} != {VECTOR_SIZE}"
            )

        embedding = data.get("embedding")

        if not isinstance(embedding, list) or len(embedding) != VECTOR_SIZE:
            raise ValueError("Invalid embedding returned by embedding service")

        return embedding

    def index_record(self, record: KnowledgeRecord) -> str:
        text = self._record_text(record)
        vector = self._embed(text)
        point_id = self._point_id(record)

        self.client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "knowledge_id": record.knowledge_id,
                        "version": record.version,
                        "topic": record.topic,
                        "category": record.category,
                        "status": record.status,
                        "source": record.source,
                        "text": text,
                        "created_at": record.created_at.isoformat(),
                        "updated_at": record.updated_at.isoformat(),
                    },
                )
            ],
        )

        return point_id

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedEvidence]:
        if not query or not query.strip():
            raise ValueError("query must not be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        vector = self._embed(query)

        results = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            with_payload=True,
        ).points

        evidence: list[RetrievedEvidence] = []

        for result in results:
            payload: dict[str, Any] = result.payload or {}
            knowledge_id = payload.get("knowledge_id")
            version = payload.get("version")

            if not knowledge_id or not version:
                continue

            record = self.store.get(knowledge_id, version)

            if record is None:
                continue

            evidence.append(
                RetrievedEvidence(
                    source_ref=record.source,
                    relative_path=f"{record.knowledge_id}/v{record.version}",
                    snippet=self._snippet(record.content),
                    score=float(result.score),
                )
            )

        return evidence

    def delete_record(self, record: KnowledgeRecord) -> None:
        point_id = self._point_id(record)

        self.client.delete(
            collection_name=self.collection,
            points_selector=[point_id],
        )

    def count(self) -> int:
        return self.client.count(
            collection_name=self.collection,
            exact=True,
        ).count

    @staticmethod
    def _record_text(record: KnowledgeRecord) -> str:
        return (
            f"Topic: {record.topic}\n"
            f"Category: {record.category}\n"
            f"Status: {record.status}\n"
            f"Source: {record.source}\n"
            f"Evidence: {record.evidence}\n"
            f"Content: {record.content}"
        )

    @staticmethod
    def _snippet(content: str, max_chars: int = 500) -> str:
        text = " ".join(content.split())
        return text[:max_chars]

    @staticmethod
    def _point_id(record: KnowledgeRecord) -> str:
        stable_key = (
            f"b3-knowledge:{record.knowledge_id}:"
            f"{record.version}"
        )
        return str(uuid5(NAMESPACE_URL, stable_key))
