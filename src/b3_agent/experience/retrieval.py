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
    RetrievalTrace,
    RetrievalTraceItem,
)
from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.learning import Learning, LearningScope, LearningStatus
from b3_agent.schemas.market_regime import MarketRegime
from b3_agent.knowledge.vector_store import VectorSearchResult


@dataclass(frozen=True)
class ExperienceRankingPolicy:
    semantic_weight: float = 0.25
    feature_weight: float = 0.25
    regime_weight: float = 0.25
    temporal_weight: float = 0.15
    confidence_weight: float = 0.10
    historical_usefulness_weight: float = 0.0
    half_life_days: float = 180.0
    learning_half_life_days: tuple[tuple[LearningScope, float | None], ...] = (
        (LearningScope.PERSONAL_EXPERIENCE, 365.0),
        (LearningScope.MARKET_OBSERVATION, 90.0),
        (LearningScope.EXTERNAL_RESEARCH, 180.0),
        (LearningScope.MODEL_DERIVED, 180.0),
        (LearningScope.COMBINED, 365.0),
    )

    def __post_init__(self) -> None:
        weights = (
            self.semantic_weight,
            self.feature_weight,
            self.regime_weight,
            self.temporal_weight,
            self.confidence_weight,
            self.historical_usefulness_weight,
        )
        if any(value < 0 for value in weights):
            raise ValueError("ranking weights must be non-negative")
        if sum(weights) <= 0:
            raise ValueError("at least one ranking weight must be positive")
        if self.half_life_days <= 0:
            raise ValueError("half_life_days must be positive")
        seen_scopes: set[LearningScope] = set()
        for scope, half_life in self.learning_half_life_days:
            if scope in seen_scopes:
                raise ValueError("learning scope decay policy must be unique")
            seen_scopes.add(scope)
            if half_life is not None and half_life <= 0:
                raise ValueError("learning half-life must be positive or None")


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
        learnings: Iterable[Learning] = (),
        historical_usefulness: dict[str, float] | None = None,
        top_k: int = 10,
    ) -> ExperienceRetrievalResult:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if top_k < 1:
            raise ValueError("top_k must be positive")

        semantic_by_reference: dict[str, float] = {}
        semantic_sources: dict[str, str] = {}
        initial_rank_by_reference: dict[str, int] = {}
        for semantic_rank, result in enumerate(semantic_results, start=1):
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
            initial_rank_by_reference.setdefault(reference, semantic_rank)

        learning_by_id = {item.learning_id: item for item in learnings}
        usefulness_by_reference = dict(historical_usefulness or {})
        for reference, score in usefulness_by_reference.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"historical usefulness for {reference} must be between 0 and 1"
                )
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

            usefulness_score = usefulness_by_reference.get(experience.experience_id)
            relevance = _weighted_score(
                semantic_score=semantic_score,
                feature_score=feature_score,
                regime_score=regime_score,
                temporal_score=temporal_score,
                confidence_score=confidence_score,
                historical_usefulness_score=usefulness_score,
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
                    historical_usefulness_score=usefulness_score,
                    fusion_score=semantic_score if semantic_score > 0 else None,
                    initial_rank=initial_rank_by_reference.get(experience.experience_id),
                )
            )

        for reference, semantic_score in semantic_by_reference.items():
            if any(match.reference_id == reference for match in matches):
                continue

            learning = learning_by_id.get(reference)
            if learning is None:
                matches.append(
                    ExperienceMatch(
                        reference_id=reference,
                        reference_type="LEARNING",
                        relevance_score=semantic_score,
                        semantic_score=semantic_score,
                        fusion_score=semantic_score,
                        initial_rank=initial_rank_by_reference.get(reference),
                    )
                )
                continue

            anchor = (
                learning.last_confirmed_at
                or learning.last_updated_at
                or learning.first_observed_at
            )
            learning_temporal_score = _temporal_score(
                anchor,
                as_of=as_of,
                half_life_days=_learning_half_life_days(
                    learning.learning_scope,
                    self.policy,
                ),
            )
            learning_confidence = learning.confidence or 0.0
            lifecycle_score = _learning_lifecycle_score(learning)
            contradiction_score = _learning_contradiction_score(learning)
            usefulness_score = usefulness_by_reference.get(reference)
            base_relevance = _weighted_score(
                semantic_score=semantic_score,
                feature_score=0.0,
                regime_score=_learning_regime_similarity(
                    learning,
                    current_regime,
                ),
                temporal_score=learning_temporal_score,
                confidence_score=learning_confidence,
                historical_usefulness_score=usefulness_score,
                policy=self.policy,
            )
            relevance = _clamp01(
                base_relevance
                * lifecycle_score
                * contradiction_score
            )
            matches.append(
                ExperienceMatch(
                    reference_id=reference,
                    reference_type="LEARNING",
                    relevance_score=relevance,
                    semantic_score=semantic_score,
                    regime_score=_learning_regime_similarity(
                        learning,
                        current_regime,
                    ),
                    temporal_score=learning_temporal_score,
                    confidence_score=learning_confidence,
                    lifecycle_score=lifecycle_score,
                    contradiction_score=contradiction_score,
                    historical_usefulness_score=usefulness_score,
                    fusion_score=semantic_score,
                    initial_rank=initial_rank_by_reference.get(reference),
                )
            )

        matches.sort(key=lambda item: (-item.relevance_score, item.reference_id))
        reranked = tuple(
            ExperienceMatch(
                reference_id=item.reference_id,
                reference_type=item.reference_type,
                relevance_score=item.relevance_score,
                semantic_score=item.semantic_score,
                feature_similarity_score=item.feature_similarity_score,
                regime_score=item.regime_score,
                temporal_score=item.temporal_score,
                confidence_score=item.confidence_score,
                lifecycle_score=item.lifecycle_score,
                contradiction_score=item.contradiction_score,
                historical_usefulness_score=item.historical_usefulness_score,
                fusion_score=item.fusion_score,
                initial_rank=item.initial_rank,
                final_rank=rank,
            )
            for rank, item in enumerate(matches, start=1)
        )
        selected = reranked[:top_k]
        trace_id = f"RTR-{current_snapshot.snapshot_id}-{current_regime.regime_id}"
        trace = RetrievalTrace(
            trace_id=trace_id,
            candidate_count=len(reranked),
            selected_count=len(selected),
            retrieval_mode=(
                "structured+hybrid-fusion"
                if semantic_by_reference
                else "structured-only"
            ),
            fusion_method="RRF" if semantic_by_reference else None,
            ranker_version="experience-ranker-v2",
            items=tuple(
                RetrievalTraceItem(
                    reference_id=item.reference_id,
                    reference_type=item.reference_type,
                    fusion_score=item.fusion_score,
                    initial_rank=item.initial_rank,
                    final_rank=item.final_rank,
                    rerank_components=tuple(
                        (name, value)
                        for name, value in (
                            ("semantic_or_fusion", item.semantic_score),
                            ("feature", item.feature_similarity_score),
                            ("regime", item.regime_score),
                            ("temporal", item.temporal_score),
                            ("confidence", item.confidence_score),
                            ("lifecycle", item.lifecycle_score),
                            ("contradiction", item.contradiction_score),
                            ("historical_usefulness", item.historical_usefulness_score),
                        )
                        if value is not None
                    ),
                )
                for item in selected
            ),
        )

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
                ("ranker", "experience-ranker-v2"),
                ("half_life_days", str(self.policy.half_life_days)),
                ("learning_decay_policy", _learning_decay_policy_label(self.policy)),
                ("historical_usefulness_weight", str(self.policy.historical_usefulness_weight)),
                ("candidate_count", str(len(reranked))),
                ("selected_count", str(len(selected))),
                ("trace_id", trace_id),
            ),
            trace=trace,
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


def _temporal_score(
    observed_at: datetime,
    *,
    as_of: datetime,
    half_life_days: float | None,
) -> float:
    age_days = max(0.0, (as_of - observed_at).total_seconds() / 86400.0)
    if half_life_days is None:
        return 1.0
    return exp(-log(2.0) * age_days / half_life_days)


def _learning_half_life_days(
    scope: LearningScope,
    policy: ExperienceRankingPolicy,
) -> float | None:
    configured = dict(policy.learning_half_life_days)
    return configured.get(scope, 180.0)


def _learning_decay_policy_label(policy: ExperienceRankingPolicy) -> str:
    return ",".join(
        f"{scope.value}:{'none' if half_life is None else half_life}"
        for scope, half_life in policy.learning_half_life_days
    )


def _learning_regime_similarity(
    learning: Learning,
    current_regime: MarketRegime,
) -> float:
    if current_regime.regime_id in learning.regime_ids:
        return 1.0

    condition_map: dict[str, str] = {}
    for condition in learning.conditions:
        if "=" not in condition:
            continue
        name, label = condition.split("=", 1)
        condition_map[name.strip().upper()] = label.strip().upper()

    current_map = {
        dimension.name.value.upper(): dimension.label.upper()
        for dimension in current_regime.dimensions
    }
    common = set(condition_map) & set(current_map)
    if not common:
        return 0.0
    return sum(
        condition_map[name] == current_map[name]
        for name in common
    ) / len(common)


def _learning_lifecycle_score(learning: Learning) -> float:
    status_factor = {
        LearningStatus.CANDIDATE: 0.70,
        LearningStatus.VALIDATING: 0.80,
        LearningStatus.ACTIVE: 1.00,
        LearningStatus.STRENGTHENING: 1.00,
        LearningStatus.WEAKENING: 0.85,
        LearningStatus.DRIFT_DETECTED: 0.65,
        LearningStatus.UNDER_REVIEW: 0.55,
        LearningStatus.SUPERSEDED: 0.25,
        LearningStatus.ARCHIVED: 0.10,
    }
    return status_factor[learning.status]


def _learning_contradiction_score(learning: Learning) -> float:
    total = len(learning.evidence_links)
    if total == 0:
        return 1.0
    contradictions = sum(
        1
        for link in learning.evidence_links
        if link.direction.value == "CONTRADICTS"
    )
    contradiction_ratio = contradictions / total
    # Contradiction lowers retrieval relevance but never deletes the learning.
    # Even fully contradicted evidence retains 50% of this factor so that
    # historical counterexamples remain retrievable and auditable.
    return 1.0 - 0.5 * contradiction_ratio


def _weighted_score(
    *,
    semantic_score: float,
    feature_score: float,
    regime_score: float,
    temporal_score: float,
    confidence_score: float,
    historical_usefulness_score: float | None,
    policy: ExperienceRankingPolicy,
) -> float:
    usefulness = (
        historical_usefulness_score
        if historical_usefulness_score is not None
        else 0.0
    )
    numerator = (
        semantic_score * policy.semantic_weight
        + feature_score * policy.feature_weight
        + regime_score * policy.regime_weight
        + temporal_score * policy.temporal_weight
        + confidence_score * policy.confidence_weight
        + usefulness * policy.historical_usefulness_weight
    )
    denominator = (
        policy.semantic_weight
        + policy.feature_weight
        + policy.regime_weight
        + policy.temporal_weight
        + policy.confidence_weight
        + policy.historical_usefulness_weight
    )
    return _clamp01(numerator / denominator)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
