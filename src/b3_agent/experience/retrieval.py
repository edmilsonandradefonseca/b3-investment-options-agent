from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp, log
from collections.abc import Iterable

from b3_agent.experience.model import Experience
from b3_agent.schemas.experience import (
    ExperienceAssessment,
    ExperienceMatch,
    ExperienceRetrievalResult,
)
from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.learning import Learning, LearningStatus
from b3_agent.schemas.market_regime import MarketRegime
from b3_agent.knowledge.vector_store import VectorSearchResult


@dataclass(frozen=True)
class ExperienceRankingPolicy:
    semantic_weight: float = 0.25
    feature_weight: float = 0.25
    regime_weight: float = 0.25
    temporal_weight: float = 0.15
    confidence_weight: float = 0.10
    half_life_days: float = 180.0

    def __post_init__(self) -> None:
        weights = (
            self.semantic_weight,
            self.feature_weight,
            self.regime_weight,
            self.temporal_weight,
            self.confidence_weight,
        )
        if any(value < 0 for value in weights):
            raise ValueError("ranking weights must be non-negative")
        if sum(weights) <= 0:
            raise ValueError("at least one ranking weight must be positive")
        if self.half_life_days <= 0:
            raise ValueError("half_life_days must be positive")


class ExperienceRanker:
    """Deterministic ranker combining structured, semantic, regime and aging signals."""

    def __init__(self, policy: ExperienceRankingPolicy | None = None):
        self.policy = policy or ExperienceRankingPolicy()

    def rank(
        self,
        *,
        current_snapshot: FeatureSnapshot,
        current_regime: MarketRegime,
        as_of: datetime,
        experiences: Iterable[Experience],
        semantic_results: Iterable[VectorSearchResult] = (),
        top_k: int = 10,
    ) -> ExperienceRetrievalResult:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if top_k < 1:
            raise ValueError("top_k must be positive")

        semantic_by_reference: dict[str, float] = {}
        semantic_sources: dict[str, str] = {}
        for result in semantic_results:
            extra = result.metadata.get("extra")
            extra = extra if isinstance(extra, dict) else {}
            reference = str(
                result.metadata.get("canonical_id")
                or result.metadata.get("learning_id")
                or extra.get("canonical_id")
                or extra.get("learning_id")
                or result.evidence_id
            )
            semantic_by_reference[reference] = max(
                semantic_by_reference.get(reference, 0.0),
                _clamp01(result.score),
            )
            semantic_sources[reference] = result.evidence_id

        matches: list[ExperienceMatch] = []
        for experience in experiences:
            if experience.operation.underlying_id != current_snapshot.subject_id:
                continue
            if experience.entry_snapshot.as_of > as_of:
                continue

            feature_score = _feature_similarity(
                current_snapshot,
                experience.entry_snapshot,
            )
            regime_score = _regime_similarity(
                current_regime,
                experience.market_regime,
            )
            temporal_score = _temporal_score(
                experience.outcome.finalized_at,
                as_of=as_of,
                half_life_days=self.policy.half_life_days,
            )
            confidence_score = experience.market_regime.confidence or 0.0
            semantic_score = semantic_by_reference.get(experience.experience_id, 0.0)

            relevance = _weighted_score(
                semantic_score=semantic_score,
                feature_score=feature_score,
                regime_score=regime_score,
                temporal_score=temporal_score,
                confidence_score=confidence_score,
                policy=self.policy,
            )
            matches.append(
                ExperienceMatch(
                    reference_id=experience.experience_id,
                    reference_type="EXPERIENCE",
                    relevance_score=relevance,
                    semantic_score=semantic_score,
                    feature_similarity_score=feature_score,
                    regime_score=regime_score,
                    temporal_score=temporal_score,
                    confidence_score=confidence_score,
                )
            )

        for reference, semantic_score in semantic_by_reference.items():
            if any(match.reference_id == reference for match in matches):
                continue
            matches.append(
                ExperienceMatch(
                    reference_id=reference,
                    reference_type="LEARNING",
                    relevance_score=semantic_score,
                    semantic_score=semantic_score,
                )
            )

        matches.sort(key=lambda item: (-item.relevance_score, item.reference_id))
        selected = tuple(matches[:top_k])

        return ExperienceRetrievalResult(
            query_id=f"EXPQ-{current_snapshot.snapshot_id}-{current_regime.regime_id}",
            as_of=as_of,
            subject_ids=(current_snapshot.subject_id,),
            matches=selected,
            current_snapshot_id=current_snapshot.snapshot_id,
            current_regime_id=current_regime.regime_id,
            source_refs=tuple(
                semantic_sources[match.reference_id]
                for match in selected
                if match.reference_id in semantic_sources
            ),
            retrieval_metadata=(
                ("ranker", "experience-ranker-v1"),
                ("half_life_days", str(self.policy.half_life_days)),
            ),
        )


class ExperienceAssessmentEngine:
    """Convert retrieval results + Learning lifecycle into bounded decision context."""

    ACTIVE_STATUSES = {
        LearningStatus.ACTIVE,
        LearningStatus.STRENGTHENING,
        LearningStatus.WEAKENING,
        LearningStatus.DRIFT_DETECTED,
        LearningStatus.UNDER_REVIEW,
    }

    def assess(
        self,
        retrieval: ExperienceRetrievalResult,
        *,
        learnings: Iterable[Learning] = (),
    ) -> ExperienceAssessment:
        learning_by_id = {item.learning_id: item for item in learnings}
        supporting: list[str] = []
        contradicting: list[str] = []
        limitations: list[str] = []

        scores = [match.relevance_score for match in retrieval.matches]
        historical_similarity = sum(scores) / len(scores) if scores else None

        confidences = [
            match.confidence_score
            for match in retrieval.matches
            if match.confidence_score is not None
        ]
        confidence = sum(confidences) / len(confidences) if confidences else None

        for match in retrieval.matches:
            learning = learning_by_id.get(match.reference_id)
            if learning is None:
                continue
            if learning.status not in self.ACTIVE_STATUSES:
                continue
            if learning.status in {
                LearningStatus.WEAKENING,
                LearningStatus.DRIFT_DETECTED,
                LearningStatus.UNDER_REVIEW,
            }:
                contradicting.append(learning.learning_id)
            else:
                supporting.append(learning.learning_id)
            if learning.selection_bias_warning:
                limitations.append(learning.selection_bias_warning)

        return ExperienceAssessment(
            historical_similarity=historical_similarity,
            confidence=confidence,
            supporting_learning_ids=tuple(dict.fromkeys(supporting)),
            contradicting_learning_ids=tuple(dict.fromkeys(contradicting)),
            applicable_regime_id=retrieval.current_regime_id,
            limitations=tuple(dict.fromkeys(limitations)),
            provenance="experience_assessment_engine:v1",
        )


def _feature_similarity(current: FeatureSnapshot, historical: FeatureSnapshot) -> float:
    current_values = _numeric_features(current)
    historical_values = _numeric_features(historical)
    common = sorted(set(current_values) & set(historical_values))
    if not common:
        return 0.0

    similarities = []
    for name in common:
        a = current_values[name]
        b = historical_values[name]
        scale = max(abs(a), abs(b), 1.0)
        similarities.append(max(0.0, 1.0 - abs(a - b) / scale))
    return sum(similarities) / len(similarities)


def _numeric_features(snapshot: FeatureSnapshot) -> dict[str, float]:
    result: dict[str, float] = {}
    for feature in snapshot.features:
        if isinstance(feature.value, bool) or not isinstance(feature.value, (int, float)):
            continue
        result[feature.name] = float(feature.value)
    return result


def _regime_similarity(current: MarketRegime, historical: MarketRegime) -> float:
    current_map = {item.name: item.label for item in current.dimensions}
    historical_map = {item.name: item.label for item in historical.dimensions}
    common = set(current_map) & set(historical_map)
    if not common:
        return 0.0
    return sum(current_map[name] == historical_map[name] for name in common) / len(common)


def _temporal_score(observed_at: datetime, *, as_of: datetime, half_life_days: float) -> float:
    age_days = max(0.0, (as_of - observed_at).total_seconds() / 86400.0)
    return exp(-log(2.0) * age_days / half_life_days)


def _weighted_score(
    *,
    semantic_score: float,
    feature_score: float,
    regime_score: float,
    temporal_score: float,
    confidence_score: float,
    policy: ExperienceRankingPolicy,
) -> float:
    numerator = (
        semantic_score * policy.semantic_weight
        + feature_score * policy.feature_weight
        + regime_score * policy.regime_weight
        + temporal_score * policy.temporal_weight
        + confidence_score * policy.confidence_weight
    )
    denominator = (
        policy.semantic_weight
        + policy.feature_weight
        + policy.regime_weight
        + policy.temporal_weight
        + policy.confidence_weight
    )
    return _clamp01(numerator / denominator)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
