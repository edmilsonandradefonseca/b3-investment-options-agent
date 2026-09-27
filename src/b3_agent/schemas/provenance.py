from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ClaimStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETRACTED = "RETRACTED"


class ClaimEvidenceDirection(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"


@dataclass(frozen=True)
class SourceDocument:
    document_id: str
    source: str
    title: str
    retrieved_at: datetime
    published_at: datetime | None = None
    source_url: str | None = None
    content_hash: str | None = None
    version: int = 1

    def __post_init__(self) -> None:
        if not self.document_id.strip() or not self.source.strip() or not self.title.strip():
            raise ValueError("document_id, source and title must be non-empty")
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        if self.published_at is not None and (
            self.published_at.tzinfo is None or self.published_at.utcoffset() is None
        ):
            raise ValueError("published_at must be timezone-aware")
        if self.version < 1:
            raise ValueError("version must be positive")


@dataclass(frozen=True)
class Claim:
    claim_id: str
    statement: str
    created_at: datetime
    status: ClaimStatus = ClaimStatus.ACTIVE
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    version: int = 1
    supersedes_claim_id: str | None = None

    def __post_init__(self) -> None:
        if not self.claim_id.strip() or not self.statement.strip():
            raise ValueError("claim_id and statement must be non-empty")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        for value in (self.valid_from, self.valid_to):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError("claim validity timestamps must be timezone-aware")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        if self.version < 1:
            raise ValueError("version must be positive")


@dataclass(frozen=True)
class ClaimEvidenceLink:
    claim_id: str
    evidence_id: str
    document_id: str
    direction: ClaimEvidenceDirection
    observed_at: datetime
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.claim_id.strip() or not self.evidence_id.strip() or not self.document_id.strip():
            raise ValueError("claim/evidence/document IDs must be non-empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
