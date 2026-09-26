from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class LearningStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    VALIDATING = "VALIDATING"
    ACTIVE = "ACTIVE"
    STRENGTHENING = "STRENGTHENING"
    WEAKENING = "WEAKENING"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class LearningScope(StrEnum):
    PERSONAL_EXPERIENCE = "PERSONAL_EXPERIENCE"
    MARKET_OBSERVATION = "MARKET_OBSERVATION"
    EXTERNAL_RESEARCH = "EXTERNAL_RESEARCH"
    MODEL_DERIVED = "MODEL_DERIVED"
    COMBINED = "COMBINED"


class EvidenceDirection(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"


@dataclass(frozen=True)
class LearningEvidenceLink:
    evidence_id: str
    direction: EvidenceDirection
    operation_id: str | None = None
    source_ref: str | None = None
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must be non-empty")
        if self.observed_at is not None and (
            self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None
        ):
            raise ValueError("observed_at must be timezone-aware")


@dataclass(frozen=True)
class Learning:
    """Reusable experience with explicit evidence, scope and lifecycle."""

    learning_id: str
    statement: str
    status: LearningStatus
    learning_scope: LearningScope
    first_observed_at: datetime
    last_updated_at: datetime

    subject_ids: tuple[str, ...] = ()
    strategy_type: str | None = None
    hypothesis: str | None = None
    conditions: tuple[str, ...] = ()
    regime_ids: tuple[str, ...] = ()
    evidence_links: tuple[LearningEvidenceLink, ...] = ()

    sample_size: int | None = None
    recent_sample_size: int | None = None
    win_rate: float | None = None
    expected_return: float | None = None
    effect_size: float | None = None
    confidence: float | None = None
    recent_confidence: float | None = None
    long_term_confidence: float | None = None

    last_confirmed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    supersedes: tuple[str, ...] = ()
    superseded_by: tuple[str, ...] = ()

    population_scope: str | None = None
    selection_bias_warning: str | None = None
    statistical_method: str | None = None
    model_version: str | None = None
    source_refs: tuple[str, ...] = ()
    provenance: str = ""
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.learning_id.strip():
            raise ValueError("learning_id must be non-empty")
        if not self.statement.strip():
            raise ValueError("statement must be non-empty")
        for value, field_name in (
            (self.first_observed_at, "first_observed_at"),
            (self.last_updated_at, "last_updated_at"),
            (self.last_confirmed_at, "last_confirmed_at"),
            (self.valid_from, "valid_from"),
            (self.valid_to, "valid_to"),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.last_updated_at < self.first_observed_at:
            raise ValueError("last_updated_at must not precede first_observed_at")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        for value, field_name in (
            (self.sample_size, "sample_size"),
            (self.recent_sample_size, "recent_sample_size"),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be non-negative")
        for value, field_name in (
            (self.win_rate, "win_rate"),
            (self.confidence, "confidence"),
            (self.recent_confidence, "recent_confidence"),
            (self.long_term_confidence, "long_term_confidence"),
        ):
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.learning_scope == LearningScope.PERSONAL_EXPERIENCE and not self.population_scope:
            raise ValueError("PERSONAL_EXPERIENCE requires population_scope")
        if self.learning_id in self.supersedes or self.learning_id in self.superseded_by:
            raise ValueError("learning cannot supersede or be superseded by itself")


@dataclass(frozen=True)
class LearningLifecycleTransition:
    learning_id: str
    from_status: LearningStatus
    to_status: LearningStatus
    changed_at: datetime
    reason: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.learning_id.strip():
            raise ValueError("learning_id must be non-empty")
        if self.changed_at.tzinfo is None or self.changed_at.utcoffset() is None:
            raise ValueError("changed_at must be timezone-aware")
        if not self.reason.strip():
            raise ValueError("reason must be non-empty")
