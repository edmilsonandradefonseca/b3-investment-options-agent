from datetime import datetime, timezone

from qdrant_client import QdrantClient

from b3_agent.knowledge.chunking import EvidenceChunker
from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider
from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
from b3_agent.knowledge.ingestion import VectorIngestionPipeline
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.knowledge.retrieval_pipeline import PointInTimeVectorRetriever
from b3_agent.knowledge.semantic_retrieval import FreshnessScorer


def _evidence(evidence_id: str, published_at: datetime) -> Evidence:
    metadata = EvidenceMetadata(
        document_id=evidence_id,
        source="test-news",
        published_at=published_at,
        retrieved_at=published_at,
        ticker_refs=("PETR4",),
    )
    return Evidence(
        evidence_id=evidence_id,
        kind=EvidenceKind.NEWS,
        title=evidence_id,
        content="PETR4 market evidence and oil context.",
        metadata=metadata,
        source_url="https://example.com/news",
    )


def test_ingestion_and_point_in_time_retrieval() -> None:
    client = QdrantClient(location=":memory:")
    embeddings = DeterministicEmbeddingProvider(dimensions=8)
    store = QdrantVectorStore(client=client, vector_size=8)
    ingestion = VectorIngestionPipeline(
        chunker=EvidenceChunker(max_chars=1200),
        embeddings=embeddings,
        store=store,
    )

    old = _evidence("old", datetime(2026, 9, 10, tzinfo=timezone.utc))
    future = _evidence("future", datetime(2026, 9, 18, tzinfo=timezone.utc))
    ingestion.ingest(old)
    ingestion.ingest(future)

    retriever = PointInTimeVectorRetriever(
        store,
        embeddings,
        freshness=FreshnessScorer(half_life_days=30),
    )
    results = retriever.retrieve(
        "PETR4 oil market",
        metadata_filter=None,
        as_of=datetime(2026, 9, 17, tzinfo=timezone.utc),
        top_k=5,
    )

    assert store.count() == 2
    assert [item.evidence_id for item in results] == ["old"]
    assert 0.0 < results[0].metadata["freshness_score"] <= 1.0


def test_metadata_filter_is_preserved() -> None:
    client = QdrantClient(location=":memory:")
    embeddings = DeterministicEmbeddingProvider(dimensions=8)
    store = QdrantVectorStore(client=client, vector_size=8)
    ingestion = VectorIngestionPipeline(
        chunker=EvidenceChunker(), embeddings=embeddings, store=store
    )
    ingestion.ingest(
        _evidence("petr", datetime(2026, 9, 16, tzinfo=timezone.utc))
    )

    retriever = PointInTimeVectorRetriever(store, embeddings)
    results = retriever.retrieve(
        "market",
        metadata_filter=__import__("b3_agent.knowledge.vector_store", fromlist=["MetadataFilter"]).MetadataFilter(ticker="petr4"),
        as_of=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    assert len(results) == 1


def test_point_in_time_rejects_evidence_not_yet_retrieved() -> None:
    client = QdrantClient(location=":memory:")
    embeddings = DeterministicEmbeddingProvider(dimensions=8)
    store = QdrantVectorStore(client=client, vector_size=8)
    ingestion = VectorIngestionPipeline(
        chunker=EvidenceChunker(max_chars=1200),
        embeddings=embeddings,
        store=store,
    )

    published = datetime(2026, 9, 10, tzinfo=timezone.utc)
    retrieved = datetime(2026, 9, 18, tzinfo=timezone.utc)
    metadata = EvidenceMetadata(
        document_id="late-ingest",
        source="test-news",
        published_at=published,
        retrieved_at=retrieved,
        ticker_refs=("PETR4",),
    )
    ingestion.ingest(
        Evidence(
            evidence_id="late-ingest",
            kind=EvidenceKind.NEWS,
            title="late-ingest",
            content="PETR4 evidence published earlier but acquired later.",
            metadata=metadata,
            source_url="https://example.com/late",
        )
    )

    retriever = PointInTimeVectorRetriever(store, embeddings)
    results = retriever.retrieve(
        "PETR4",
        as_of=datetime(2026, 9, 17, tzinfo=timezone.utc),
        top_k=5,
    )

    assert results == ()
