from datetime import datetime, timezone

from qdrant_client import QdrantClient

from b3_agent.knowledge.chunking import EvidenceChunker
from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider
from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.knowledge.vector_store import MetadataFilter


def _chunk(text: str, ticker: str = "PETR4"):
    metadata = EvidenceMetadata(
        document_id="doc-1",
        source="test:market",
        published_at=datetime(2026, 9, 17, 10, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 9, 17, 10, 5, tzinfo=timezone.utc),
        ticker_refs=(ticker,),
        topic="market",
    )
    evidence = Evidence(
        evidence_id=f"ev-{ticker}",
        kind=EvidenceKind.NEWS,
        title="Market evidence",
        content=text,
        metadata=metadata,
    )
    return EvidenceChunker(max_chars=1000).chunk(evidence)[0]


def test_qdrant_upsert_search_filter_delete() -> None:
    client = QdrantClient(":memory:")
    store = QdrantVectorStore(client=client, collection_name="test", vector_size=8)
    embedding_provider = DeterministicEmbeddingProvider(dimensions=8)
    chunk = _chunk("PETR4 reacts to market rates")
    embedding = embedding_provider.embed((chunk.content,))[0]

    store.upsert((chunk,), (embedding,))

    assert store.count() == 1
    results = store.search(embedding, top_k=3, metadata_filter=MetadataFilter(ticker="petr4"))
    assert len(results) == 1
    assert results[0].chunk_id == chunk.chunk_id
    assert results[0].evidence_id == chunk.evidence_id
    assert results[0].metadata["topic"] == "market"

    store.delete((chunk.chunk_id,))
    assert store.count() == 0
