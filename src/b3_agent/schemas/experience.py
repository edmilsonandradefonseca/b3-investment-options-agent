from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RetrievalTraceItem:
    reference_id: str
    reference_type: str
    fusion_score: float | None = None
    initial_rank: int | None = None
    final_rank: int | None = None
    rerank_components: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if not self.reference_id.strip():
            raise ValueError("reference_id must be non-empty")
        if not self.reference_type.strip():
            raise ValueError("reference_type must be non-empty")
        if self.fusion_score is not None and not 0.0 <= self.fusion_score <= 1.0:
            raise ValueError("fusion_score must be between 0 and 1")
        for name, rank in (("initial_rank", self.initial_rank), ("final_rank", self.final_rank)):
            if rank is not None and rank < 1:
                raise ValueError(f"{name} must be positive")
        for component, value in self.rerank_components:
            if not component.strip():
                raise ValueError("rerank component name must be non-empty")
            if not 0.0 <= value <= 1.0:
                raise ValueError("rerank component values must be between 0 and 1")


@dataclass(frozen=True)
class RetrievalTrace:
    trace_id: str
    candidate_count: int
    selected_count: int
    items: tuple[RetrievalTraceItem, ...] = ()
    retrieval_mode: str = "structured+dense"
    fusion_method: str | None = None
    ranker_version: str = "experience-ranker-v2"

    def __post_init__(self) -> None:
        if not self.trace_id.strip():
            raise ValueError("trace_id must be non-empty")
        if self.candidate_count < 0 or self.selected_count < 0:
            raise ValueError("retrieval trace counts must be non-negative")
        if self.selected_count > self.candidate_count:
            raise ValueError("selected_count cannot exceed candidate_count")
        if not self.retrieval_mode.strip():
            raise ValueError("retrieval_mode must be non-empty")


@dataclass(frozen=True)
class ExperienceMatch:
    reference_id: str
    reference_type: str
    relevance_score: float
    semantic_score: float | None = None
    feature_similarity_score: float | None = None
    regime_score: float | None = None
    temporal_score: float | None = None
    confidence_score: float | None = None
    lifecycle_score: float | None = None
    contradiction_score: float | None = None
    historical_usefulness_score: float | None = None
    fusion_score: float | None = None
    initial_rank: int | None = None
    final_rank: int | None = None

    def __post_init__(self) -> None:
        if not self.reference_id.strip():
            raise ValueError("reference_id must be non-empty")
        if not self.reference_type.strip():
            raise ValueError("reference_type must be non-empty")
        for value, field_name in (
            (self.relevance_score, "relevance_score"),
            (self.semantic_score, "semantic_score"),
            (self.feature_similarity_score, "feature_similarity_score"),
            (self.regime_score, "regime_score"),
            (self.temporal_score, "temporal_score"),
            (self.confidence_score, "confidence_score"),
            (self.lifecycle_score, "lifecycle_score"),
            (self.contradiction_score, "contradiction_score"),
            (self.historical_usefulness_score, "historical_usefulness_score"),
            (self.fusion_score, "fusion_score"),
        ):
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        for name, rank in (("initial_rank", self.initial_rank), ("final_rank", self.final_rank)):
            if rank is not None and rank < 1:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class ExperienceRetrievalResult:
    query_id: str
    as_of: datetime
    subject_ids: tuple[str, ...]
    matches: tuple[ExperienceMatch, ...]
    current_snapshot_id: str | None = None
    current_regime_id: str | None = None
    source_refs: tuple[str, ...] = ()
    retrieval_metadata: tuple[tuple[str, str], ...] = ()
    trace: RetrievalTrace | None = None

    def __post_init__(self) -> None:
        if not self.query_id.strip():
            raise ValueError("query_id must be non-empty")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")


@dataclass(frozen=True)
class ExperienceAssessment:
    historical_similarity: float | None
    confidence: float | None
    supporting_learning_ids: tuple[str, ...] = ()
    contradicting_learning_ids: tuple[str, ...] = ()
    recent_evidence_ids: tuple[str, ...] = ()
    long_term_evidence_ids: tuple[str, ...] = ()
    applicable_regime_id: str | None = None
    limitations: tuple[str, ...] = ()
    provenance: str = ""

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.historical_similarity, "historical_similarity"),
            (self.confidence, "confidence"),
        ):
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
