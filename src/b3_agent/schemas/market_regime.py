from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RegimeDimensionName(StrEnum):
    TREND = "TREND"
    VOLATILITY = "VOLATILITY"
    RISK_APPETITE = "RISK_APPETITE"
    RATES = "RATES"
    FOREIGN_FLOW = "FOREIGN_FLOW"
    COMMODITY = "COMMODITY"


@dataclass(frozen=True)
class RegimeDimension:
    name: RegimeDimensionName
    label: str
    score: float | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("regime dimension label must be non-empty")


@dataclass(frozen=True)
class MarketRegime:
    """Reproducible point-in-time market-state classification."""

    regime_id: str
    as_of: datetime
    dimensions: tuple[RegimeDimension, ...]
    classifier_version: str
    feature_snapshot_id: str
    confidence: float | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source_refs: tuple[str, ...] = ()
    provenance: str = ""
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.regime_id.strip():
            raise ValueError("regime_id must be non-empty")
        if not self.classifier_version.strip():
            raise ValueError("classifier_version must be non-empty")
        if not self.feature_snapshot_id.strip():
            raise ValueError("feature_snapshot_id must be non-empty")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for value, field_name in (
            (self.valid_from, "valid_from"),
            (self.valid_to, "valid_to"),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        names = [dimension.name for dimension in self.dimensions]
        if len(names) != len(set(names)):
            raise ValueError("regime dimensions must be unique")
