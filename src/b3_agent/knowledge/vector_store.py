from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, Sequence

from .chunking import EvidenceChunk
from .embeddings import Embedding


@dataclass(frozen=True)
class MetadataFilter:
    """Minimal provider-neutral metadata filters for vector retrieval."""

    ticker: str | None = None
    topic: str | None = None
    source: str | None = None
    published_before: datetime | None = None
    published_after: datetime | None = None
    valid_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.ticker is not None and not self.ticker.strip():
            raise ValueError("ticker filter must not be empty")
        if self.topic is not None and not self.topic.strip():
            raise ValueError("topic filter must not be empty")
        if self.source is not None and not self.source.strip():
            raise ValueError("source filter must not be empty")
        for name, value in (
            ("published_before", self.published_before),
            ("published_after", self.published_after),
            ("valid_at", self.valid_at),
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")
        if (
            self.published_before is not None
            and self.published_after is not None
            and self.published_before < self.published_after
        ):
            raise ValueError("published_before must be >= published_after")

    @property
    def normalized_ticker(self) -> str | None:
        return self.ticker.strip().upper() if self.ticker is not None else None


@dataclass(frozen=True)
class VectorSearchResult:
    """Provider-neutral result returned by a vector search."""

    chunk_id: str
    evidence_id: str
    score: float
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.chunk_id.strip() or not self.evidence_id.strip():
            raise ValueError("chunk_id and evidence_id must not be empty")
        if not self.content.strip():
            raise ValueError("content must not be empty")


class VectorStore(Protocol):
    """Minimal abstraction implemented by a vector database adapter."""

    def upsert(
        self,
        chunks: Sequence[EvidenceChunk],
        embeddings: Sequence[Embedding],
    ) -> None: ...

    def search(
        self,
        embedding: Embedding,
        *,
        top_k: int = 5,
        metadata_filter: MetadataFilter | None = None,
    ) -> tuple[VectorSearchResult, ...]: ...

    def delete(self, chunk_ids: Sequence[str]) -> None: ...

    def count(self) -> int: ...
