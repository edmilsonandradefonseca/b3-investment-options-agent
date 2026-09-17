from __future__ import annotations

from hashlib import sha256
from typing import Any, Sequence
from uuid import UUID, uuid5

from qdrant_client import QdrantClient, models

from .chunking import EvidenceChunk
from .embeddings import Embedding
from .vector_store import MetadataFilter, VectorSearchResult

_NAMESPACE = UUID("4f9f0d3c-3e31-4d9f-a3d8-4f8f2a8b7e11")


class QdrantVectorStore:
    """Small Qdrant adapter implementing the provider-neutral VectorStore contract."""

    def __init__(
        self,
        *,
        client: QdrantClient,
        collection_name: str = "b3_evidence",
        vector_size: int = 8,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if vector_size < 1:
            raise ValueError("vector_size must be positive")
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    def upsert(
        self,
        chunks: Sequence[EvidenceChunk],
        embeddings: Sequence[Embedding],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return
        points: list[models.PointStruct] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            if len(embedding.values) != self.vector_size:
                raise ValueError("embedding dimension does not match collection")
            points.append(
                models.PointStruct(
                    id=_point_id(chunk.chunk_id),
                    vector=list(embedding.values),
                    payload=_payload(chunk),
                )
            )
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(
        self,
        embedding: Embedding,
        *,
        top_k: int = 5,
        metadata_filter: MetadataFilter | None = None,
    ) -> tuple[VectorSearchResult, ...]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if len(embedding.values) != self.vector_size:
            raise ValueError("embedding dimension does not match collection")
        query_filter = _build_filter(metadata_filter)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=list(embedding.values),
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        results: list[VectorSearchResult] = []
        for point in response.points:
            payload = dict(point.payload or {})
            results.append(
                VectorSearchResult(
                    chunk_id=str(payload["chunk_id"]),
                    evidence_id=str(payload["evidence_id"]),
                    score=float(point.score),
                    content=str(payload["content"]),
                    metadata=payload,
                )
            )
        return tuple(results)

    def delete(self, chunk_ids: Sequence[str]) -> None:
        if not chunk_ids:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=[_point_id(chunk_id) for chunk_id in chunk_ids]
            ),
        )

    def count(self) -> int:
        return int(self.client.count(collection_name=self.collection_name, exact=True).count)


def _point_id(chunk_id: str) -> str:
    return str(uuid5(_NAMESPACE, chunk_id))


def _payload(chunk: EvidenceChunk) -> dict[str, Any]:
    metadata = chunk.metadata
    return {
        "chunk_id": chunk.chunk_id,
        "evidence_id": chunk.evidence_id,
        "content": chunk.content,
        "document_id": metadata.document_id,
        "source": metadata.source,
        "published_at": _timestamp(metadata.published_at),
        "retrieved_at": _timestamp(metadata.retrieved_at),
        "valid_from": _timestamp(metadata.valid_from),
        "valid_to": _timestamp(metadata.valid_to),
        "ticker_refs": list(metadata.ticker_refs),
        "sector_refs": list(metadata.sector_refs),
        "event_refs": list(metadata.event_refs),
        "topic": metadata.topic,
        "source_quality": metadata.source_quality,
        "confidence": metadata.confidence,
        "retention_class": metadata.retention_class.value,
        "decay_profile": metadata.decay_profile.value,
        "extra": dict(metadata.extra),
    }


def _timestamp(value: Any) -> float | None:
    return value.timestamp() if value is not None else None


def _build_filter(metadata_filter: MetadataFilter | None) -> models.Filter | None:
    if metadata_filter is None:
        return None
    must: list[models.FieldCondition] = []
    if metadata_filter.normalized_ticker:
        must.append(
            models.FieldCondition(
                key="ticker_refs",
                match=models.MatchValue(value=metadata_filter.normalized_ticker),
            )
        )
    if metadata_filter.topic:
        must.append(
            models.FieldCondition(
                key="topic",
                match=models.MatchValue(value=metadata_filter.topic),
            )
        )
    if metadata_filter.source:
        must.append(
            models.FieldCondition(
                key="source",
                match=models.MatchValue(value=metadata_filter.source),
            )
        )
    if metadata_filter.published_before or metadata_filter.published_after:
        must.append(
            models.FieldCondition(
                key="published_at",
                range=models.Range(
                    lte=_timestamp(metadata_filter.published_before),
                    gte=_timestamp(metadata_filter.published_after),
                ),
            )
        )
    if metadata_filter.valid_at:
        timestamp = _timestamp(metadata_filter.valid_at)
        must.extend(
            [
                models.FieldCondition(
                    key="valid_from",
                    range=models.Range(lte=timestamp),
                ),
                models.FieldCondition(
                    key="valid_to",
                    range=models.Range(gte=timestamp),
                ),
            ]
        )
    return models.Filter(must=must) if must else None
