from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FeatureDomain(StrEnum):
    MARKET = "MARKET"
    OPTION = "OPTION"
    PORTFOLIO = "PORTFOLIO"
    MACRO = "MACRO"
    FLOW = "FLOW"
    FX = "FX"
    COMMODITY = "COMMODITY"
    EVENT = "EVENT"
    RISK = "RISK"


@dataclass(frozen=True)
class FeatureValue:
    name: str
    value: float | int | str | bool | None
    domain: FeatureDomain
    available_at: datetime
    unit: str | None = None
    source_ref: str | None = None
    quality_status: str = "VALID"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("feature name must be non-empty")
        if self.available_at.tzinfo is None or self.available_at.utcoffset() is None:
            raise ValueError("feature available_at must be timezone-aware")


@dataclass(frozen=True)
class FeatureSnapshot:
    """Immutable point-in-time context for an operation or analysis."""

    snapshot_id: str
    subject_id: str
    as_of: datetime
    features: tuple[FeatureValue, ...]
    operation_id: str | None = None
    regime_id: str | None = None
    event_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALID"
    provenance: str = ""
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.snapshot_id.strip():
            raise ValueError("snapshot_id must be non-empty")
        if not self.subject_id.strip():
            raise ValueError("subject_id must be non-empty")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if any(feature.available_at > self.as_of for feature in self.features):
            raise ValueError("feature available_at must not exceed snapshot as_of")
        if any(not value.strip() for value in self.event_refs):
            raise ValueError("event_refs must not contain empty values")
        if any(not value.strip() for value in self.source_refs):
            raise ValueError("source_refs must not contain empty values")
