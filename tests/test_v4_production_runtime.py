from __future__ import annotations

import json
from io import BytesIO
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock
from types import SimpleNamespace

from qdrant_client import QdrantClient

from b3_agent.knowledge.chunking import EvidenceChunker
from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider, HttpEmbeddingProvider
from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.knowledge.retrieval import VectorEvidenceRetriever


class _Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def test_http_embedding_provider_validates_768d(monkeypatch):
    payload = {
        "embedding": [0.01] * 768,
        "dimensions": 768,
        "model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    }

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(json.dumps(payload).encode("utf-8")),
    )

    provider = HttpEmbeddingProvider(base_url="http://embedding", dimensions=768)
    result = provider.embed(("PETR4 valuation",))

    assert len(result) == 1
    assert len(result[0].values) == 768
    assert result[0].model == payload["model"]


def test_vector_evidence_retriever_uses_hybrid_qdrant():
    embeddings = DeterministicEmbeddingProvider(dimensions=768)
    store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="b3_test_hybrid",
        vector_size=768,
        hybrid=True,
    )
    evidence = Evidence(
        evidence_id="EV-PETR4",
        kind=EvidenceKind.ANALYTICAL,
        title="PETR4 evidence",
        content="PETR4 dividend and valuation evidence",
        metadata=EvidenceMetadata(
            document_id="DOC-PETR4",
            source="test:runtime",
            published_at=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            retrieved_at=datetime(2026, 9, 27, 12, 1, tzinfo=timezone.utc),
            ticker_refs=("PETR4",),
            topic="market",
        ),
    )
    chunk = EvidenceChunker(max_chars=1000).chunk(evidence)[0]
    store.upsert((chunk,), embeddings.embed((chunk.content,)))

    retriever = VectorEvidenceRetriever(store, embeddings)
    results = retriever.retrieve("PETR4 valuation", top_k=3)

    assert len(results) == 1
    assert results[0].source_ref == "test:runtime"
    assert results[0].relative_path == "DOC-PETR4"
    assert "PETR4" in results[0].snippet


def test_production_runtime_builds_shared_qdrant_and_neo4j(monkeypatch):
    import b3_agent.orchestration.runtime as runtime

    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("B3_QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("B3_NEO4J_URI", "bolt://neo4j:7687")
    monkeypatch.setenv("B3_NEO4J_USER", "neo4j")
    monkeypatch.setenv("B3_EMBEDDING_URL", "http://embedding:8093")

    qdrant_client = Mock()
    qdrant_client.collection_exists.return_value = True
    qdrant_client.get_collection.return_value = SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(
                vectors={"dense": SimpleNamespace(size=768)},
                sparse_vectors={"sparse": object()},
            )
        )
    )
    monkeypatch.setattr(runtime, "QdrantClient", lambda url: qdrant_client)

    driver = MagicMock()
    monkeypatch.setattr(
        runtime.GraphDatabase,
        "driver",
        lambda uri, auth: driver,
    )

    retriever, graph = runtime._production_knowledge_context()

    driver.verify_connectivity.assert_called_once()
    assert retriever.store.collection_name == runtime.B3_V4_QDRANT_COLLECTION
    assert retriever.store.vector_size == 768
    assert retriever.store.hybrid is True
    assert retriever.embeddings.base_url == "http://embedding:8093"
    assert graph.driver is driver
