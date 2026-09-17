from __future__ import annotations

from datetime import datetime
from math import exp, log
from typing import Protocol

from .embeddings import EmbeddingProvider
from .vector_store import MetadataFilter, VectorSearchResult, VectorStore


class RetrievalStrategy(Protocol):
    """Contract for a retrieval strategy over a vector store."""

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        metadata_filter: MetadataFilter | None = None,
        as_of: datetime | None = None,
    ) -> tuple[VectorSearchResult, ...]: ...


class FreshnessScorer:
    """Provider-neutral freshness score with an explicit half-life."""

    def __init__(self, *, half_life_days: float = 30.0) -> None:
        if half_life_days <= 0:
            raise ValueError("half_life_days must be positive")
        self.half_life_days = half_life_days

    def score(self, published_at: datetime | None, *, as_of: datetime) -> float:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        if published_at is None:
            return 1.0
        if published_at.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        age_days = max(0.0, (as_of - published_at).total_seconds() / 86400.0)
        return exp(-log(2.0) * age_days / self.half_life_days)


class VectorRetriever:
    """Minimal semantic retriever; ranking policy intentionally remains simple."""

    def __init__(self, store: VectorStore, embeddings: EmbeddingProvider) -> None:
        self.store = store
        self.embeddings = embeddings

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        metadata_filter: MetadataFilter | None = None,
        as_of: datetime | None = None,
    ) -> tuple[VectorSearchResult, ...]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if as_of is not None and as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        query_embedding = self.embeddings.embed((query.strip(),))[0]
        return self.store.search(
            query_embedding,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
