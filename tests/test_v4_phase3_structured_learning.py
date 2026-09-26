from datetime import datetime, timedelta, timezone

import pytest

from b3_agent.experience.model import ExperienceEngine
from b3_agent.learning import LearningEngine, LearningPolicy
from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.market_regime import (
    MarketRegime,
    RegimeDimension,
    RegimeDimensionName,
)
from b3_agent.schemas.operation import Operation, OperationDirection, OperationStatus
from b3_agent.schemas.outcome import Outcome, OutcomeStatus
from b3_agent.schemas.learning import LearningScope, LearningStatus


BASE = datetime(2026, 4, 1, 15, 0, tzinfo=timezone.utc)


def make_experience(index: int, *, win: bool = True, subject: str = "B3-PETR4", strategy: str = "SHORT_PUT"):
    opened = BASE + timedelta(days=index * 3)
    closed = opened + timedelta(days=10)
    operation_id = f"OP-{index:03d}"
    snapshot_id = f"FS-{index:03d}"

    operation = Operation(
        operation_id=operation_id,
        strategy_type=strategy,
        underlying_id=subject,
        opened_at=opened,
        closed_at=closed,
        status=OperationStatus.CLOSED,
        direction=OperationDirection.SHORT,
        quantity=100,
        source_transaction_ids=(f"TX-{index:03d}-O", f"TX-{index:03d}-C"),
    )
    snapshot = FeatureSnapshot(
        snapshot_id=snapshot_id,
        subject_id=subject,
        as_of=opened,
        features=(),
        operation_id=operation_id,
        quality_status="VALID",
    )
    regime = MarketRegime(
        regime_id=f"REG-{index:03d}",
        as_of=opened,
        dimensions=(
            RegimeDimension(RegimeDimensionName.TREND, "SIDEWAYS"),
            RegimeDimension(RegimeDimensionName.VOLATILITY, "HIGH"),
            RegimeDimension(RegimeDimensionName.FOREIGN_FLOW, "POSITIVE"),
        ),
        classifier_version="regime-v1",
        feature_snapshot_id=snapshot_id,
        confidence=0.75,
    )
    pnl = 300.0 if win else -250.0
    ret = 0.03 if win else -0.025
    outcome = Outcome(
        outcome_id=f"OUT-{index:03d}",
        operation_id=operation_id,
        finalized_at=closed,
        status=OutcomeStatus.FINAL,
        realized_pnl=pnl,
        realized_return=ret,
        holding_period_days=10,
    )
    return ExperienceEngine().assemble(
        operation=operation,
        entry_snapshot=snapshot,
        market_regime=regime,
        outcome=outcome,
    )


def test_experience_engine_builds_deterministic_validated_aggregate():
    experience = make_experience(1)
    same = make_experience(1)

    assert experience == same
    assert experience.experience_id.startswith("EXP-")
    assert experience.outcome.operation_id == experience.operation.operation_id


def test_experience_engine_rejects_regime_from_different_snapshot():
    exp = make_experience(1)
    wrong_regime = MarketRegime(
        regime_id="REG-WRONG",
        as_of=exp.market_regime.as_of,
        dimensions=exp.market_regime.dimensions,
        classifier_version="regime-v1",
        feature_snapshot_id="FS-OTHER",
    )

    with pytest.raises(ValueError, match="derived from entry snapshot"):
        ExperienceEngine().assemble(
            operation=exp.operation,
            entry_snapshot=exp.entry_snapshot,
            market_regime=wrong_regime,
            outcome=exp.outcome,
        )


def test_learning_status_progresses_with_configurable_sample_policy():
    engine = LearningEngine(
        LearningPolicy(
            min_validating_sample=3,
            min_active_sample=8,
            robust_sample_size=25,
            recent_window=5,
        )
    )
    experiences = [make_experience(i) for i in range(1, 9)]

    candidate = engine.learn(experiences[:1], as_of=BASE + timedelta(days=50))
    validating = engine.learn(experiences[:4], as_of=BASE + timedelta(days=51))
    active = engine.learn(experiences[:8], as_of=BASE + timedelta(days=52))

    assert candidate.learning.status == LearningStatus.CANDIDATE
    assert validating.learning.status == LearningStatus.VALIDATING
    assert active.learning.status == LearningStatus.ACTIVE
    assert active.learning.learning_scope == LearningScope.PERSONAL_EXPERIENCE


def test_learning_preserves_supporting_and_contradicting_experience():
    experiences = [
        make_experience(1, win=True),
        make_experience(2, win=False),
        make_experience(3, win=True),
        make_experience(4, win=False),
    ]
    result = LearningEngine().learn(
        experiences,
        as_of=BASE + timedelta(days=100),
    )

    directions = [link.direction.value for link in result.learning.evidence_links]
    assert directions.count("SUPPORTS") == 2
    assert directions.count("CONTRADICTS") == 2
    assert result.statistics.win_rate == pytest.approx(0.5)
    assert result.statistics.expected_return == pytest.approx(0.0025)
    assert result.learning.selection_bias_warning is not None
    assert "must not be generalized" in result.learning.selection_bias_warning


def test_learning_id_is_stable_for_same_subject_strategy_and_regime():
    engine = LearningEngine()
    first = engine.learn(
        [make_experience(i) for i in range(1, 4)],
        as_of=BASE + timedelta(days=100),
    )
    second = engine.learn(
        [make_experience(i) for i in range(1, 6)],
        as_of=BASE + timedelta(days=110),
        previous=first.learning,
    )

    assert first.learning.learning_id == second.learning.learning_id
    assert second.learning.sample_size == 5


def test_learning_rejects_mixed_subject_or_regime_cohort():
    engine = LearningEngine()

    with pytest.raises(ValueError, match="same underlying subject"):
        engine.learn(
            [make_experience(1), make_experience(2, subject="B3-VALE3")],
            as_of=BASE + timedelta(days=100),
        )

    exp = make_experience(3)
    changed_regime = MarketRegime(
        regime_id="REG-CHANGED",
        as_of=exp.market_regime.as_of,
        dimensions=(
            RegimeDimension(RegimeDimensionName.TREND, "BEAR"),
            RegimeDimension(RegimeDimensionName.VOLATILITY, "HIGH"),
            RegimeDimension(RegimeDimensionName.FOREIGN_FLOW, "POSITIVE"),
        ),
        classifier_version="regime-v1",
        feature_snapshot_id=exp.entry_snapshot.snapshot_id,
    )
    changed = ExperienceEngine().assemble(
        operation=exp.operation,
        entry_snapshot=exp.entry_snapshot,
        market_regime=changed_regime,
        outcome=exp.outcome,
    )

    with pytest.raises(ValueError, match="same regime signature"):
        engine.learn(
            [make_experience(1), changed],
            as_of=BASE + timedelta(days=100),
        )


def test_recent_deterioration_can_trigger_drift_and_explicit_transition():
    policy = LearningPolicy(
        min_validating_sample=3,
        min_active_sample=8,
        robust_sample_size=25,
        recent_window=5,
        min_recent_for_drift=5,
        strengthening_delta=0.15,
        weakening_delta=0.15,
        drift_delta=0.30,
    )
    engine = LearningEngine(policy)

    initial = [make_experience(i, win=True) for i in range(1, 9)]
    previous = engine.learn(
        initial,
        as_of=BASE + timedelta(days=100),
    )
    assert previous.learning.status == LearningStatus.ACTIVE

    deteriorated = initial + [
        make_experience(i, win=False) for i in range(9, 14)
    ]
    updated = engine.learn(
        deteriorated,
        as_of=BASE + timedelta(days=140),
        previous=previous.learning,
    )

    assert updated.learning.status == LearningStatus.DRIFT_DETECTED
    assert updated.statistics.recent_win_rate == 0.0
    assert updated.transition is not None
    assert updated.transition.from_status == LearningStatus.ACTIVE
    assert updated.transition.to_status == LearningStatus.DRIFT_DETECTED


def test_confidence_is_sample_based_not_claimed_statistical_significance():
    policy = LearningPolicy(
        min_validating_sample=2,
        min_active_sample=4,
        robust_sample_size=16,
        recent_window=4,
    )
    engine = LearningEngine(policy)
    small = engine.learn(
        [make_experience(1), make_experience(2)],
        as_of=BASE + timedelta(days=50),
    )
    larger = engine.learn(
        [make_experience(i) for i in range(1, 9)],
        as_of=BASE + timedelta(days=80),
    )

    assert small.learning.confidence == pytest.approx((2 / 16) ** 0.5)
    assert larger.learning.confidence == pytest.approx((8 / 16) ** 0.5)
    assert larger.learning.confidence > small.learning.confidence
    assert larger.learning.statistical_method == "descriptive-personal-cohort-v1"
