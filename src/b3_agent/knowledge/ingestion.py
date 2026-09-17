from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .chunking import EvidenceChunk, EvidenceChunker
from .embeddings import EmbeddingProvider
from .evidence import Evidence
from .vector_store import VectorStore


@dataclass(frozen=True)
class VectorIngestionResult:
    """Small audit-friendly result for one evidence ingestion operation."""

    evidence_id: str
    chunk_ids: tuple[str, ...]


class VectorIngestionPipeline:
    """Deterministic Evidence -> Chunk -> Embedding -> VectorStore pipeline."""

    def __init__(
        self,
        *,
        chunker: EvidenceChunker,
        embeddings: EmbeddingProvider,
        store: VectorStore,
    ) -> None:
        self.chunker = chunker
        self.embeddings = embeddings
        self.store = store

    def ingest(self, evidence: Evidence) -> VectorIngestionResult:
        chunks: Sequence[EvidenceChunk] = self.chunker.chunk(evidence)
        embeddings = self.embeddings.embed(tuple(chunk.content for chunk in chunks))
        self.store.upsert(chunks, embeddings)
        return VectorIngestionResult(
            evidence_id=evidence.evidence_id,
            chunk_ids=tuple(chunk.chunk_id for chunk in chunks),
        )
