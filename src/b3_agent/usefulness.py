from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from b3_agent.schemas.usefulness import (
    DecisionEvidenceOutcomeAttribution,
    HistoricalUsefulnessAssessment,
    OutcomeAssociation,
)


@dataclass(frozen=True)
class HistoricalUsefulnessPolicy:
    """Conservative association scoring with neutral-prior shrinkage."""

    prior_score: float = 0.5
    prior_weight: float = 4.0
    inconclusive_value: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.prior_score <= 1.0:
            raise ValueError("prior_score must be between 0 and 1")
        if self.prior_weight < 0:
            raise ValueError("prior_weight must be non-negative")
        if not 0.0 <= self.inconclusive_value <= 1.0:
            raise ValueError("inconclusive_value must be between 0 and 1")


class HistoricalUsefulnessEngine:
    """Estimate historical usefulness without converting outcomes into truth claims."""

    def __init__(self, policy: HistoricalUsefulnessPolicy | None = None) -> None:
        self.policy = policy or HistoricalUsefulnessPolicy()

    def assess(
        self,
        evidence_ref: str,
        observations: Iterable[DecisionEvidenceOutcomeAttribution],
    ) -> HistoricalUsefulnessAssessment:
        if not evidence_ref.strip():
            raise ValueError("evidence_ref must be non-empty")

        selected = tuple(item for item in observations if item.evidence_ref == evidence_ref)
        positive = sum(
            item.attribution_confidence
            for item in selected
            if item.association == OutcomeAssociation.POSITIVE
        )
        negative = sum(
            item.attribution_confidence
            for item in selected
            if item.association == OutcomeAssociation.NEGATIVE
        )
        inconclusive = sum(
            item.attribution_confidence
            for item in selected
            if item.association == OutcomeAssociation.INCONCLUSIVE
        )
        effective = positive + negative + inconclusive
        numerator = (
            self.policy.prior_score * self.policy.prior_weight
            + positive
            + self.policy.inconclusive_value * inconclusive
        )
        denominator = self.policy.prior_weight + effective
        score = self.policy.prior_score if denominator == 0 else numerator / denominator

        return HistoricalUsefulnessAssessment(
            evidence_ref=evidence_ref,
            usefulness_score=max(0.0, min(1.0, score)),
            observation_count=len(selected),
            effective_weight=effective,
            positive_weight=positive,
            negative_weight=negative,
            inconclusive_weight=inconclusive,
        )

    def assess_many(
        self,
        observations: Iterable[DecisionEvidenceOutcomeAttribution],
    ) -> dict[str, HistoricalUsefulnessAssessment]:
        materialized = tuple(observations)
        return {
            ref: self.assess(ref, materialized)
            for ref in sorted({item.evidence_ref for item in materialized})
        }
