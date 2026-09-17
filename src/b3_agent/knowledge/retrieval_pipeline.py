from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from .embeddings import EmbeddingProvider
from .semantic_retrieval import FreshnessScorer
from .vector_store import MetadataFilter, VectorSearchResult, VectorStore


class PointInTimeVectorRetriever:
    """Small retrieval facade adding point-in-time filtering and freshness metadata."""

    def __init__(
        self,
        store: VectorStore,
        embeddings: EmbeddingProvider,
        *,
        freshness: FreshnessScorer | None = None,
    ) -> None:
        self.store = store
        self.embeddings = embeddings
        self.freshness = freshness

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

        effective_filter = _with_point_in_time(metadata_filter, as_of)
        embedding = self.embeddings.embed((query.strip(),))[0]
        results = self.store.search(
            embedding,
            top_k=top_k,
            metadata_filter=effective_filter,
        )

        if self.freshness is None or as_of is None:
            return results

        enriched = []
        for result in results:
            published_at = _as_datetime(result.metadata.get("published_at"))
            metadata = dict(result.metadata)
            metadata["freshness_score"] = self.freshness.score(
                published_at, as_of=as_of
            )
            enriched.append(replace(result, metadata=metadata))
        return tuple(enriched)


def _with_point_in_time(
    metadata_filter: MetadataFilter | None,
    as_of: datetime | None,
) -> MetadataFilter | None:
    if as_of is None:
        return metadata_filter

    if metadata_filter is None:
        return MetadataFilter(published_before=as_of, valid_at=as_of)

    published_before = metadata_filter.published_before
    if published_before is None or as_of < published_before:
        published_before = as_of

    return MetadataFilter(
        ticker=metadata_filter.ticker,
        topic=metadata_filter.topic,
        source=metadata_filter.source,
        published_before=published_before,
        published_after=metadata_filter.published_after,
        valid_at=metadata_filter.valid_at or as_of,
    )


def _as_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).astimezone()
    return None
