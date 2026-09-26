from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AnalysisRun:
    """Lightweight persisted/read-only reference for comparing analyses over time."""

    analysis_id: str
    as_of: datetime
    request_scope: str
    feature_snapshot_id: str | None = None
    market_regime_id: str | None = None
    relevant_learning_ids: tuple[str, ...] = ()
    opportunity_refs: tuple[str, ...] = ()
    risk_refs: tuple[str, ...] = ()
    rationale_ref: str | None = None
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.analysis_id.strip():
            raise ValueError("analysis_id must be non-empty")
        if not self.request_scope.strip():
            raise ValueError("request_scope must be non-empty")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.quality_status not in {"VALIDATED", "WARNING", "REJECTED"}:
            raise ValueError("invalid quality_status")


@dataclass(frozen=True)
class AnalysisChange:
    field: str
    before: object
    after: object


@dataclass(frozen=True)
class AnalysisChangeSet:
    previous_analysis_id: str
    current_analysis_id: str
    changes: tuple[AnalysisChange, ...]
