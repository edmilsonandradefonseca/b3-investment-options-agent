from __future__ import annotations

from collections import Counter
from hashlib import sha256
from math import log
import re
from typing import Any, Sequence
from uuid import UUID, uuid5

from qdrant_client import QdrantClient, models

from .chunking import EvidenceChunk
from .embeddings import Embedding
from .vector_store import MetadataFilter, VectorSearchResult

_NAMESPACE = UUID("4f9f0d3c-3e31-4d9f-a3d8-4f8f2a8b7e11")
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")


class QdrantVectorStore:
    """Qdrant adapter with optional dense+sparse hybrid retrieval.

    The default mode preserves the legacy single dense-vector collection.
    hybrid=True creates named dense and sparse vectors and enables
    Qdrant-native Reciprocal Rank Fusion (RRF).
    """

    def __init__(
        self,
        *,
        client: QdrantClient,
        collection_name: str = "b3_evidence",
        vector_size: int = 8,
        hybrid: bool = False,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if vector_size < 1:
            raise ValueError("vector_size must be positive")
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.hybrid = hybrid
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection_name):
            return
        if self.hybrid:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(),
                },
            )
            return
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
            vector: Any
            if self.hybrid:
                vector = {
                    "dense": list(embedding.values),
                    "sparse": _lexical_sparse_vector(chunk.content),
                }
            else:
                vector = list(embedding.values)
            points.append(
                models.PointStruct(
                    id=_point_id(chunk.chunk_id),
                    vector=vector,
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
        kwargs: dict[str, Any] = {}
        if self.hybrid:
            kwargs["using"] = "dense"
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=list(embedding.values),
            query_filter=_build_filter(metadata_filter),
            limit=top_k,
            with_payload=True,
            **kwargs,
        )
        return _results(response.points)

    def hybrid_search(
        self,
        query_text: str,
        embedding: Embedding,
        *,
        top_k: int = 5,
        prefetch_k: int | None = None,
        metadata_filter: MetadataFilter | None = None,
    ) -> tuple[VectorSearchResult, ...]:
        """Fuse dense semantic and sparse lexical retrieval with Qdrant RRF."""
        if not self.hybrid:
            raise RuntimeError("hybrid_search requires QdrantVectorStore(hybrid=True)")
        if not query_text.strip():
            raise ValueError("query_text must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if len(embedding.values) != self.vector_size:
            raise ValueError("embedding dimension does not match collection")

        prefetch_limit = prefetch_k or max(top_k * 4, top_k)
        if prefetch_limit < top_k:
            raise ValueError("prefetch_k must be >= top_k")

        query_filter = _build_filter(metadata_filter)
        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=list(embedding.values),
                    using="dense",
                    query_filter=query_filter,
                    limit=prefetch_limit,
                ),
                models.Prefetch(
                    query=_lexical_sparse_vector(query_text),
                    using="sparse",
                    query_filter=query_filter,
                    limit=prefetch_limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        return _results(response.points)

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
        return int(
            self.client.count(
                collection_name=self.collection_name,
                exact=True,
            ).count
        )


def _results(points: Sequence[Any]) -> tuple[VectorSearchResult, ...]:
    results: list[VectorSearchResult] = []
    for point in points:
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


def _lexical_sparse_vector(text: str) -> models.SparseVector:
    """Create a dependency-light deterministic lexical sparse vector."""
    tokens = [token.casefold() for token in _TOKEN_RE.findall(text)]
    if not tokens:
        raise ValueError("text must contain at least one lexical token")

    counts = Counter(tokens)
    by_index: dict[int, float] = {}
    for token, count in counts.items():
        index = int.from_bytes(sha256(token.encode("utf-8")).digest()[:4], "big")
        value = 1.0 + log(float(count))
        by_index[index] = by_index.get(index, 0.0) + value

    ordered = sorted(by_index.items())
    return models.SparseVector(
        indices=[index for index, _ in ordered],
        values=[value for _, value in ordered],
    )


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


def _build_filter(
    metadata_filter: MetadataFilter | None,
) -> models.Filter | None:
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
        must.append(
            models.FieldCondition(
                key="valid_from",
                range=models.Range(lte=timestamp),
            )
        )
    return models.Filter(must=must) if must else None
