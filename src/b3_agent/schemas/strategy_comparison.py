from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

AS_OF = date | datetime


@dataclass(frozen=True)
class StrategyAlternative:
    alternative_id: str
    label: str
    action_type: str
    subject_id: str
    as_of: AS_OF
    capital_required: float | None = None
    expected_return: float | None = None
    max_loss: float | None = None
    liquidity_score: float | None = None
    portfolio_impact: float | None = None
    historical_similarity: float | None = None
    experience_confidence: float | None = None
    payoff_by_scenario: dict[str, float] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"

    def __post_init__(self) -> None:
        if not self.alternative_id.strip():
            raise ValueError("alternative_id must be non-empty")
        if not self.label.strip():
            raise ValueError("label must be non-empty")
        if not self.action_type.strip():
            raise ValueError("action_type must be non-empty")
        if not self.subject_id.strip():
            raise ValueError("subject_id must be non-empty")
        if self.capital_required is not None and self.capital_required < 0:
            raise ValueError("capital_required must be non-negative")
        for value, field_name in (
            (self.liquidity_score, "liquidity_score"),
            (self.historical_similarity, "historical_similarity"),
            (self.experience_confidence, "experience_confidence"),
        ):
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.quality_status not in {"VALIDATED", "WARNING", "REJECTED"}:
            raise ValueError("invalid quality_status")


@dataclass(frozen=True)
class StrategyComparison:
    comparison_id: str
    as_of: AS_OF
    alternatives: tuple[StrategyAlternative, ...]
    capital_delta: float | None
    expected_return_delta: float | None
    max_loss_delta: float | None
    liquidity_delta: float | None
    portfolio_impact_delta: float | None
    historical_similarity_delta: float | None
    experience_confidence_delta: float | None
    scenario_deltas: dict[str, float] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"

    def __post_init__(self) -> None:
        if not self.comparison_id.strip():
            raise ValueError("comparison_id must be non-empty")
        if len(self.alternatives) != 2:
            raise ValueError("StrategyComparison currently requires exactly two alternatives")
        if self.quality_status not in {"VALIDATED", "WARNING", "REJECTED"}:
            raise ValueError("invalid quality_status")
