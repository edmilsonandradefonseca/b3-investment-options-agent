from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import sqrt
from statistics import fmean, median
from collections.abc import Iterable

from b3_agent.experience.model import Experience
from b3_agent.schemas.learning import (
    EvidenceDirection,
    Learning,
    LearningEvidenceLink,
    LearningLifecycleTransition,
    LearningScope,
    LearningStatus,
)


@dataclass(frozen=True)
class LearningPolicy:
    """Configurable V1 thresholds; policy values are not architecture invariants."""

    min_validating_sample: int = 3
    min_active_sample: int = 8
    robust_sample_size: int = 25
    recent_window: int = 5
    min_recent_for_drift: int = 4
    strengthening_delta: float = 0.15
    weakening_delta: float = 0.15
    drift_delta: float = 0.30

    def __post_init__(self) -> None:
        if self.min_validating_sample < 1:
            raise ValueError("min_validating_sample must be positive")
        if self.min_active_sample < self.min_validating_sample:
            raise ValueError("min_active_sample must be >= min_validating_sample")
        if self.robust_sample_size < self.min_active_sample:
            raise ValueError("robust_sample_size must be >= min_active_sample")
        if self.recent_window < 1:
            raise ValueError("recent_window must be positive")
        if self.min_recent_for_drift < 1:
            raise ValueError("min_recent_for_drift must be positive")
        for value, name in (
            (self.strengthening_delta, "strengthening_delta"),
            (self.weakening_delta, "weakening_delta"),
            (self.drift_delta, "drift_delta"),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class LearningStatistics:
    sample_size: int
    wins: int
    losses: int
    win_rate: float | None
    expected_return: float | None
    median_return: float | None
    recent_sample_size: int
    recent_win_rate: float | None
    sample_confidence: float


@dataclass(frozen=True)
class LearningUpdateResult:
    learning: Learning
    statistics: LearningStatistics
    transition: LearningLifecycleTransition | None = None


class LearningEngine:
    """Deterministic V1 learning updater over validated personal experiences."""

    ENGINE_VERSION = "learning-engine-v1"

    def __init__(self, policy: LearningPolicy | None = None):
        self.policy = policy or LearningPolicy()

    def learn(
        self,
        experiences: Iterable[Experience],
        *,
        as_of: datetime,
        previous: Learning | None = None,
    ) -> LearningUpdateResult:
        ordered = tuple(
            sorted(
                experiences,
                key=lambda item: (
                    item.outcome.finalized_at,
                    item.experience_id,
                ),
            )
        )
        if not ordered:
            raise ValueError("experiences must not be empty")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        subject_ids = {item.operation.underlying_id for item in ordered}
        strategy_types = {item.operation.strategy_type for item in ordered}
        signatures = {_regime_signature(item) for item in ordered}

        if len(subject_ids) != 1:
            raise ValueError("all experiences must share the same underlying subject")
        if len(strategy_types) != 1:
            raise ValueError("all experiences must share the same strategy_type")
        if len(signatures) != 1:
            raise ValueError("all experiences must share the same regime signature")

        subject_id = next(iter(subject_ids))
        strategy_type = next(iter(strategy_types))
        regime_signature = next(iter(signatures))
        statistics = self._statistics(ordered)

        learning_id = _learning_id(
            subject_id=subject_id,
            strategy_type=strategy_type,
            regime_signature=regime_signature,
        )

        if previous is not None and previous.learning_id != learning_id:
            raise ValueError("previous learning does not match experience cohort")

        status = self._status(statistics, previous)
        evidence_links = tuple(
            LearningEvidenceLink(
                evidence_id=f"EXP-EVIDENCE-{item.experience_id}",
                direction=(
                    EvidenceDirection.SUPPORTS
                    if _is_win(item)
                    else EvidenceDirection.CONTRADICTS
                ),
                operation_id=item.operation.operation_id,
                source_ref=item.experience_id,
                observed_at=item.outcome.finalized_at,
            )
            for item in ordered
        )

        supporting_dates = [
            item.outcome.finalized_at for item in ordered if _is_win(item)
        ]
        first_observed_at = min(item.operation.opened_at for item in ordered)
        conditions = tuple(regime_signature.split("|"))
        regime_ids = tuple(dict.fromkeys(item.market_regime.regime_id for item in ordered))

        statement = (
            f"Observed personal experience for {strategy_type} on {subject_id} "
            f"under {', '.join(conditions)}: "
            f"{statistics.wins}/{statistics.sample_size} positive outcomes"
        )

        learning = Learning(
            learning_id=learning_id,
            statement=statement,
            status=status,
            learning_scope=LearningScope.PERSONAL_EXPERIENCE,
            population_scope=(
                f"user historical operations for {subject_id}/{strategy_type} "
                f"matching regime {regime_signature}"
            ),
            first_observed_at=first_observed_at,
            last_updated_at=as_of,
            subject_ids=(subject_id,),
            strategy_type=strategy_type,
            hypothesis=(
                f"{strategy_type} on {subject_id} may have favorable outcomes "
                f"under regime {regime_signature}"
            ),
            conditions=conditions,
            regime_ids=regime_ids,
            evidence_links=evidence_links,
            sample_size=statistics.sample_size,
            recent_sample_size=statistics.recent_sample_size,
            win_rate=statistics.win_rate,
            expected_return=statistics.expected_return,
            confidence=statistics.sample_confidence,
            recent_confidence=_recent_confidence(statistics, self.policy),
            long_term_confidence=statistics.sample_confidence,
            last_confirmed_at=max(supporting_dates) if supporting_dates else None,
            valid_from=first_observed_at,
            statistical_method="descriptive-personal-cohort-v1",
            model_version=self.ENGINE_VERSION,
            selection_bias_warning=(
                "Personal operations were selected by the investor; observed "
                "frequencies must not be generalized to market-wide probabilities."
            ),
            source_refs=tuple(item.experience_id for item in ordered),
            provenance="learning_engine:v1",
            schema_version="1.0",
        )

        transition = None
        if previous is not None and previous.status != learning.status:
            transition = LearningLifecycleTransition(
                learning_id=learning.learning_id,
                from_status=previous.status,
                to_status=learning.status,
                changed_at=as_of,
                reason=_transition_reason(previous.status, learning.status, statistics),
                evidence_refs=tuple(item.experience_id for item in ordered[-self.policy.recent_window :]),
            )

        return LearningUpdateResult(
            learning=learning,
            statistics=statistics,
            transition=transition,
        )

    def _statistics(self, experiences: tuple[Experience, ...]) -> LearningStatistics:
        sample_size = len(experiences)
        wins = sum(1 for item in experiences if _is_win(item))
        losses = sample_size - wins
        win_rate = wins / sample_size if sample_size else None

        returns = [
            item.outcome.realized_return
            for item in experiences
            if item.outcome.realized_return is not None
        ]
        recent = experiences[-self.policy.recent_window :]
        recent_wins = sum(1 for item in recent if _is_win(item))
        recent_win_rate = recent_wins / len(recent) if recent else None

        return LearningStatistics(
            sample_size=sample_size,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            expected_return=fmean(returns) if returns else None,
            median_return=median(returns) if returns else None,
            recent_sample_size=len(recent),
            recent_win_rate=recent_win_rate,
            sample_confidence=min(
                1.0,
                sqrt(sample_size / self.policy.robust_sample_size),
            ),
        )

    def _status(
        self,
        statistics: LearningStatistics,
        previous: Learning | None,
    ) -> LearningStatus:
        if statistics.sample_size < self.policy.min_validating_sample:
            return LearningStatus.CANDIDATE
        if statistics.sample_size < self.policy.min_active_sample:
            return LearningStatus.VALIDATING

        if (
            previous is not None
            and statistics.recent_sample_size >= self.policy.min_recent_for_drift
            and statistics.win_rate is not None
            and statistics.recent_win_rate is not None
        ):
            delta = statistics.recent_win_rate - statistics.win_rate
            if abs(delta) >= self.policy.drift_delta:
                return LearningStatus.DRIFT_DETECTED
            if delta >= self.policy.strengthening_delta:
                return LearningStatus.STRENGTHENING
            if delta <= -self.policy.weakening_delta:
                return LearningStatus.WEAKENING

        return LearningStatus.ACTIVE


def _is_win(experience: Experience) -> bool:
    pnl = experience.outcome.realized_pnl
    return pnl is not None and pnl > 0


def _regime_signature(experience: Experience) -> str:
    return "|".join(
        f"{dimension.name.value}={dimension.label}"
        for dimension in experience.market_regime.dimensions
    )


def _learning_id(
    *,
    subject_id: str,
    strategy_type: str,
    regime_signature: str,
) -> str:
    digest = sha256(
        f"{subject_id}|{strategy_type}|{regime_signature}".encode("utf-8")
    ).hexdigest()[:16]
    return f"LRN-{digest}"


def _recent_confidence(
    statistics: LearningStatistics,
    policy: LearningPolicy,
) -> float:
    return min(
        1.0,
        sqrt(statistics.recent_sample_size / policy.recent_window),
    )


def _transition_reason(
    previous: LearningStatus,
    current: LearningStatus,
    statistics: LearningStatistics,
) -> str:
    return (
        f"Learning status changed from {previous.value} to {current.value}; "
        f"sample={statistics.sample_size}, recent_sample={statistics.recent_sample_size}, "
        f"win_rate={statistics.win_rate}, recent_win_rate={statistics.recent_win_rate}."
    )
