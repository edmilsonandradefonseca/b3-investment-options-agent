from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AlternativeAssessment:
    """Derived qualitative assessment linked to a supplied alternative or asset."""

    alternative_id: str
    priority_rank: int = 0
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()
    decision_implications: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionProposal:
    """Structured investment recommendation produced by the reasoning layer."""

    action: str
    subject_id: str
    thesis: str
    rationale: str
    evidence_refs: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    opportunity_cost: str = ""
    capital_impact: str = ""
    confidence: str = "UNKNOWN"
    invalidation_conditions: tuple[str, ...] = ()
    as_of: datetime | None = None
    alternative_assessments: tuple[AlternativeAssessment, ...] = ()


@dataclass(frozen=True)
class RiskValidation:
    """Deterministic gate over a proposed decision."""

    status: str
    reasons: tuple[str, ...] = ()

    @property
    def approved(self) -> bool:
        return self.status == "PASS"
