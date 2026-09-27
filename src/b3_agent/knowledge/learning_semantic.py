from __future__ import annotations

from datetime import datetime
from collections.abc import Iterable

from b3_agent.knowledge.chunking import EvidenceChunker
from b3_agent.knowledge.embeddings import EmbeddingProvider
from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.knowledge.vector_store import MetadataFilter, VectorSearchResult
from b3_agent.schemas.learning import Learning


B3_SEMANTIC_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
B3_SEMANTIC_DIMENSIONS = 768
B3_SEMANTIC_COLLECTION = "b3_memory_768"


class LearningSemanticIndex:
    """Project Learning objects into Qdrant and retrieve semantic candidates."""

    def __init__(
        self,
        *,
        store: QdrantVectorStore,
        embeddings: EmbeddingProvider,
    ) -> None:
        if store.vector_size != B3_SEMANTIC_DIMENSIONS:
            raise ValueError(
                f"B3 semantic memory requires {B3_SEMANTIC_DIMENSIONS} dimensions"
            )
        self.store = store
        self.embeddings = embeddings

    def upsert(self, learnings: Iterable[Learning]) -> None:
        for learning in learnings:
            evidence = _learning_evidence(learning)
            chunks = EvidenceChunker(max_chars=2000).chunk(evidence)
            vectors = self.embeddings.embed(tuple(chunk.content for chunk in chunks))
            self.store.upsert(chunks, vectors)

    def search(
        self,
        query: str,
        *,
        as_of: datetime,
        ticker: str | None = None,
        top_k: int = 10,
    ) -> tuple[VectorSearchResult, ...]:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        embedding = self.embeddings.embed((query,))[0]
        metadata_filter = MetadataFilter(
            ticker=ticker,
            topic="learning",
            published_before=as_of,
        )
        search_k = max(top_k, top_k * 3)
        if self.store.hybrid:
            results = self.store.hybrid_search(
                query,
                embedding,
                top_k=search_k,
                prefetch_k=max(search_k * 2, search_k),
                metadata_filter=metadata_filter,
            )
        else:
            results = self.store.search(
                embedding,
                top_k=search_k,
                metadata_filter=metadata_filter,
            )
        valid = []
        for result in results:
            valid_from = result.metadata.get("valid_from")
            valid_to = result.metadata.get("valid_to")
            if valid_from is not None and float(valid_from) > as_of.timestamp():
                continue
            if valid_to is not None and float(valid_to) < as_of.timestamp():
                continue
            valid.append(result)
        return tuple(valid[:top_k])


def _learning_evidence(learning: Learning) -> Evidence:
    tickers = tuple(
        subject.removeprefix("B3-").upper()
        for subject in learning.subject_ids
        if subject.strip()
    )
    content = "\n".join(
        part
        for part in (
            learning.statement,
            learning.hypothesis or "",
            "Conditions: " + ", ".join(learning.conditions) if learning.conditions else "",
            f"Status: {learning.status.value}",
            f"Scope: {learning.learning_scope.value}",
            f"Confidence: {learning.confidence}" if learning.confidence is not None else "",
            learning.selection_bias_warning or "",
        )
        if part
    )
    metadata = EvidenceMetadata(
        document_id=learning.learning_id,
        source=f"learning:{learning.learning_id}",
        published_at=learning.first_observed_at,
        retrieved_at=learning.last_updated_at,
        ticker_refs=tickers,
        topic="learning",
        source_quality="derived",
        confidence=learning.confidence if learning.confidence is not None else 0.0,
        valid_from=learning.valid_from or learning.first_observed_at,
        valid_to=learning.valid_to,
        extra={
            "canonical_id": learning.learning_id,
            "learning_id": learning.learning_id,
            "canonical_version": learning.schema_version,
            "learning_status": learning.status.value,
            "learning_scope": learning.learning_scope.value,
        },
    )
    return Evidence(
        evidence_id=f"LEARNING-{learning.learning_id}",
        kind=EvidenceKind.ANALYTICAL,
        title=f"Learning {learning.learning_id}",
        content=content,
        metadata=metadata,
    )
