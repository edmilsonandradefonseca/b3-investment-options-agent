from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from .lifecycle import DecayProfile, RetentionClass


class EvidenceKind(StrEnum):
    NEWS = "news"
    MARKET_RESEARCH = "market_research"
    OBSIDIAN_NOTE = "obsidian_note"
    DOCUMENT = "document"
    ANALYTICAL = "analytical"


@dataclass(frozen=True)
class EvidenceMetadata:
    """Typed metadata required for temporal, provenance-aware RAG retrieval."""

    document_id: str
    source: str
    published_at: datetime | None
    retrieved_at: datetime
    ticker_refs: tuple[str, ...] = ()
    sector_refs: tuple[str, ...] = ()
    event_refs: tuple[str, ...] = ()
    topic: str = ""
    source_quality: str = "unknown"
    confidence: float = 1.0
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    retention_class: RetentionClass = RetentionClass.MARKET_EVIDENCE
    decay_profile: DecayProfile = DecayProfile.FAST
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id must not be empty")
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        if self.published_at is not None and (
            self.published_at.tzinfo is None or self.published_at.utcoffset() is None
        ):
            raise ValueError("published_at must be timezone-aware")
        if self.valid_from is not None and (
            self.valid_from.tzinfo is None or self.valid_from.utcoffset() is None
        ):
            raise ValueError("valid_from must be timezone-aware")
        if self.valid_to is not None and (
            self.valid_to.tzinfo is None or self.valid_to.utcoffset() is None
        ):
            raise ValueError("valid_to must be timezone-aware")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        normalized_tickers = tuple(dict.fromkeys(t.strip().upper() for t in self.ticker_refs if t.strip()))
        object.__setattr__(self, "ticker_refs", normalized_tickers)
        object.__setattr__(self, "sector_refs", tuple(dict.fromkeys(s.strip().upper() for s in self.sector_refs if s.strip())))
        object.__setattr__(self, "event_refs", tuple(dict.fromkeys(e.strip() for e in self.event_refs if e.strip())))

    def is_available_at(self, as_of: datetime) -> bool:
        """Return whether this evidence was available and valid at ``as_of``."""
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.published_at is not None and self.published_at > as_of:
            return False
        if self.retrieved_at > as_of:
            return False
        if self.valid_from is not None and as_of < self.valid_from:
            return False
        if self.valid_to is not None and as_of > self.valid_to:
            return False
        return True


@dataclass(frozen=True)
class Evidence:
    """Canonical source evidence consumed by the future RAG pipeline."""

    evidence_id: str
    kind: EvidenceKind
    title: str
    content: str
    metadata: EvidenceMetadata
    source_url: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.content.strip():
            raise ValueError("content must not be empty")
        if self.source_url is not None:
            parsed = urlparse(self.source_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("source_url must be an absolute http(s) URL")

    def available_at(self, as_of: datetime) -> bool:
        return self.metadata.is_available_at(as_of)

    @property
    def source_ref(self) -> str:
        return self.metadata.source
