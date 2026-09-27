from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OutcomeAssociation(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class DecisionEvidenceOutcomeAttribution:
    """Observed association between one decision evidence item and a later outcome.

    This is deliberately not a causal or truth claim. attribution_confidence
    expresses how much weight this observation may carry when estimating
    historical usefulness.
    """

    attribution_id: str
    decision_id: str
    evidence_ref: str
    outcome_id: str
    observed_at: datetime
    association: OutcomeAssociation
    attribution_confidence: float
    rationale: str = ""
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("attribution_id", self.attribution_id),
            ("decision_id", self.decision_id),
            ("evidence_ref", self.evidence_ref),
            ("outcome_id", self.outcome_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if not 0.0 <= self.attribution_confidence <= 1.0:
            raise ValueError("attribution_confidence must be between 0 and 1")
        if any(not ref.strip() for ref in self.source_refs):
            raise ValueError("source_refs must not contain empty values")


@dataclass(frozen=True)
class HistoricalUsefulnessAssessment:
    evidence_ref: str
    usefulness_score: float
    observation_count: int
    effective_weight: float
    positive_weight: float
    negative_weight: float
    inconclusive_weight: float
    method: str = "weighted-association-shrinkage-v1"

    def __post_init__(self) -> None:
        if not self.evidence_ref.strip():
            raise ValueError("evidence_ref must be non-empty")
        if not 0.0 <= self.usefulness_score <= 1.0:
            raise ValueError("usefulness_score must be between 0 and 1")
        if self.observation_count < 0:
            raise ValueError("observation_count must be non-negative")
        for name, value in (
            ("effective_weight", self.effective_weight),
            ("positive_weight", self.positive_weight),
            ("negative_weight", self.negative_weight),
            ("inconclusive_weight", self.inconclusive_weight),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
