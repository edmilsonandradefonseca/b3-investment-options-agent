from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

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

        effective_filter, temporal_filter = _with_point_in_time(metadata_filter, as_of)
        embedding = self.embeddings.embed((query.strip(),))[0]

        # Temporal validity is intentionally enforced after vector retrieval.
        # Qdrant payloads may contain nullable valid_from/valid_to values, and
        # provider-neutral VectorStore implementations are not required to
        # support SQL-like NULL interval semantics. Over-fetching preserves
        # enough candidates for post-filtering when some hits are invalid.
        search_k = max(top_k, top_k * 5) if temporal_filter is not None else top_k
        results = self.store.search(
            embedding,
            top_k=search_k,
            metadata_filter=effective_filter,
        )

        if temporal_filter is not None:
            results = tuple(
                result for result in results if _is_valid_at(result, temporal_filter)
            )[:top_k]

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
) -> tuple[MetadataFilter | None, datetime | None]:
    """Separate push-down-safe filters from nullable interval validation."""
    if as_of is None:
        return metadata_filter, metadata_filter.valid_at if metadata_filter else None

    published_before = as_of
    valid_at = as_of
    if metadata_filter is None:
        return MetadataFilter(published_before=published_before), valid_at

    if metadata_filter.published_before is not None:
        published_before = min(published_before, metadata_filter.published_before)

    return MetadataFilter(
        ticker=metadata_filter.ticker,
        topic=metadata_filter.topic,
        source=metadata_filter.source,
        published_before=published_before,
        published_after=metadata_filter.published_after,
    ), metadata_filter.valid_at or valid_at


def _is_valid_at(result: VectorSearchResult, valid_at: datetime) -> bool:
    published_at = _as_datetime(result.metadata.get("published_at"))
    retrieved_at = _as_datetime(result.metadata.get("retrieved_at"))
    valid_from = _as_datetime(result.metadata.get("valid_from"))
    valid_to = _as_datetime(result.metadata.get("valid_to"))

    if published_at is not None and published_at > valid_at:
        return False
    # retrieved_at is the earliest explicit system-availability timestamp in
    # the current EvidenceMetadata contract. Historical replay must not use
    # evidence that the system had not acquired yet.
    if retrieved_at is not None and retrieved_at > valid_at:
        return False
    if valid_from is not None and valid_from > valid_at:
        return False
    if valid_to is not None and valid_to < valid_at:
        return False
    return True


def _as_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return None
