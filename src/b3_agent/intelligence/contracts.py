from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class AcquisitionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    EMPTY = "EMPTY"
    FAILED = "FAILED"
    AUTH_FAILED = "AUTH_FAILED"


class EvidenceConclusion(StrEnum):
    MATERIAL_FOUND = "MATERIAL_FOUND"
    NO_MATERIAL_FOUND = "NO_MATERIAL_FOUND"
    COVERAGE_INSUFFICIENT = "COVERAGE_INSUFFICIENT"


@dataclass(frozen=True)
class ProviderResultEnvelope:
    provider: str
    started_at: datetime
    completed_at: datetime
    status: AcquisitionStatus
    raw_result_count: int = 0
    normalized_result_count: int = 0
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    fallback_used: bool = False
    next_cursor: str | None = None
    coverage_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, name in (
            (self.started_at, "started_at"),
            (self.completed_at, "completed_at"),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")
        if self.raw_result_count < 0 or self.normalized_result_count < 0:
            raise ValueError("result counts must be non-negative")
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
