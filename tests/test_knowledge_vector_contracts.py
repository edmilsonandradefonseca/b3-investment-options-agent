from datetime import datetime, timezone

import pytest

from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider
from b3_agent.knowledge.semantic_retrieval import FreshnessScorer, VectorRetriever
from b3_agent.knowledge.vector_store import MetadataFilter, VectorSearchResult


class FakeVectorStore:
    def __init__(self) -> None:
        self.calls = []

    def search(self, embedding, *, top_k=5, metadata_filter=None):
        self.calls.append((embedding, top_k, metadata_filter))
        return (
            VectorSearchResult(
                chunk_id="e1:0:abc",
                evidence_id="e1",
                score=0.91,
                content="PETR4 market evidence",
                metadata={"ticker_refs": ["PETR4"]},
            ),
        )


def test_metadata_filter_normalizes_ticker_and_validates_timestamps() -> None:
    as_of = datetime(2026, 9, 17, tzinfo=timezone.utc)
    filters = MetadataFilter(ticker=" petr4 ", valid_at=as_of)
    assert filters.normalized_ticker == "PETR4"


def test_metadata_filter_rejects_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        MetadataFilter(valid_at=datetime(2026, 9, 17))


def test_vector_retriever_embeds_query_and_delegates_to_store() -> None:
    store = FakeVectorStore()
    retriever = VectorRetriever(store, DeterministicEmbeddingProvider())
    result = retriever.retrieve(
        "PETR4 news",
        top_k=3,
        metadata_filter=MetadataFilter(ticker="PETR4"),
    )
    assert len(result) == 1
    assert store.calls[0][1] == 3
    assert store.calls[0][2].normalized_ticker == "PETR4"


def test_vector_retriever_rejects_invalid_query_and_limit() -> None:
    retriever = VectorRetriever(FakeVectorStore(), DeterministicEmbeddingProvider())
    with pytest.raises(ValueError, match="query"):
        retriever.retrieve(" ")
    with pytest.raises(ValueError, match="top_k"):
        retriever.retrieve("PETR4", top_k=0)


def test_freshness_score_is_bounded_and_recent_is_higher() -> None:
    scorer = FreshnessScorer(half_life_days=30)
    as_of = datetime(2026, 9, 17, tzinfo=timezone.utc)
    recent = scorer.score(datetime(2026, 9, 16, tzinfo=timezone.utc), as_of=as_of)
    old = scorer.score(datetime(2026, 6, 17, tzinfo=timezone.utc), as_of=as_of)
    assert 0 < old < recent <= 1


def test_freshness_requires_timezone_aware_as_of() -> None:
    scorer = FreshnessScorer()
    with pytest.raises(ValueError, match="timezone-aware"):
        scorer.score(None, as_of=datetime(2026, 9, 17))
