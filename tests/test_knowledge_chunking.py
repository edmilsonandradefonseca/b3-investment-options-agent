from datetime import datetime, timezone

import pytest

from b3_agent.knowledge.chunking import EvidenceChunker
from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata


def _evidence(content: str) -> Evidence:
    metadata = EvidenceMetadata(
        document_id="doc-1",
        source="test:market",
        published_at=datetime(2026, 9, 17, 10, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 9, 17, 10, 5, tzinfo=timezone.utc),
        ticker_refs=("petr4",),
        topic="rates",
    )
    return Evidence(
        evidence_id="ev-1",
        kind=EvidenceKind.NEWS,
        title="Market evidence",
        content=content,
        metadata=metadata,
        source_url="https://example.com/news",
    )


def test_chunks_are_bounded_and_deterministic() -> None:
    evidence = _evidence("Primeiro parágrafo longo.\n\nSegundo parágrafo longo.")
    chunker = EvidenceChunker(max_chars=25)

    first = chunker.chunk(evidence)
    second = chunker.chunk(evidence)

    assert first == second
    assert len(first) > 1
    assert all(0 < len(chunk.content) <= 25 for chunk in first)
    assert [chunk.chunk_index for chunk in first] == list(range(len(first)))


def test_metadata_is_propagated_to_every_chunk() -> None:
    chunks = EvidenceChunker(max_chars=20).chunk(_evidence("alpha beta gamma delta epsilon"))

    assert all(chunk.metadata.document_id == "doc-1" for chunk in chunks)
    assert all(chunk.metadata.source == "test:market" for chunk in chunks)
    assert all(chunk.metadata.ticker_refs == ("PETR4",) for chunk in chunks)
    assert all(chunk.metadata.extra["parent_evidence_id"] == "ev-1" for chunk in chunks)
    assert all(chunk.metadata.extra["chunk_count"] == len(chunks) for chunk in chunks)
    assert all(chunk.metadata.extra["chunk_content_hash"] for chunk in chunks)


def test_chunk_identity_changes_when_content_changes() -> None:
    evidence_a = _evidence("alpha beta gamma")
    evidence_b = _evidence("alpha beta delta")

    chunk_a = EvidenceChunker(max_chars=100).chunk(evidence_a)[0]
    chunk_b = EvidenceChunker(max_chars=100).chunk(evidence_b)[0]

    assert chunk_a.chunk_id != chunk_b.chunk_id


def test_invalid_chunker_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        EvidenceChunker(max_chars=0)
