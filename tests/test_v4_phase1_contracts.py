from datetime import datetime, timezone

import pytest

from b3_agent.schemas.experience import (
    ExperienceAssessment,
    ExperienceMatch,
    ExperienceRetrievalResult,
)
from b3_agent.schemas.feature_snapshot import FeatureDomain, FeatureSnapshot, FeatureValue
from b3_agent.schemas.learning import (
    EvidenceDirection,
    Learning,
    LearningEvidenceLink,
    LearningLifecycleTransition,
    LearningScope,
    LearningStatus,
)
from b3_agent.schemas.market_regime import MarketRegime, RegimeDimension, RegimeDimensionName
from b3_agent.schemas.outcome import Outcome, OutcomeStatus


def ts(day: int, hour: int = 15) -> datetime:
    return datetime(2026, 9, day, hour, 0, tzinfo=timezone.utc)


def test_feature_snapshot_enforces_point_in_time_availability():
    snapshot = FeatureSnapshot(
        snapshot_id="FS-001",
        subject_id="B3-PETR4",
        as_of=ts(10),
        features=(
            FeatureValue(
                name="close",
                value=42.0,
                domain=FeatureDomain.MARKET,
                available_at=ts(10, 14),
                unit="BRL",
                source_ref="brapi:PETR4",
            ),
            FeatureValue(
                name="foreign_flow_5d",
                value=1200.0,
                domain=FeatureDomain.FLOW,
                available_at=ts(9),
                unit="BRL_mn",
            ),
        ),
        operation_id="OP-001",
    )

    assert snapshot.operation_id == "OP-001"
    assert len(snapshot.features) == 2


def test_feature_snapshot_rejects_future_feature():
    with pytest.raises(ValueError, match="must not exceed snapshot as_of"):
        FeatureSnapshot(
            snapshot_id="FS-FUTURE",
            subject_id="B3-PETR4",
            as_of=ts(10),
            features=(
                FeatureValue(
                    name="future_news",
                    value=True,
                    domain=FeatureDomain.EVENT,
                    available_at=ts(11),
                ),
            ),
        )


def test_outcome_supports_finalized_operation_result():
    outcome = Outcome(
        outcome_id="OUT-001",
        operation_id="OP-001",
        finalized_at=ts(20),
        status=OutcomeStatus.FINAL,
        realized_pnl=850.0,
        realized_return=0.034,
        holding_period_days=19,
        max_adverse_excursion=-0.08,
        max_favorable_excursion=0.05,
        capital_used=25000.0,
    )

    assert outcome.status == OutcomeStatus.FINAL
    assert outcome.realized_pnl == 850.0


def test_market_regime_is_multidimensional_and_versioned():
    regime = MarketRegime(
        regime_id="REG-001",
        as_of=ts(10),
        dimensions=(
            RegimeDimension(RegimeDimensionName.TREND, "SIDEWAYS", 0.82),
            RegimeDimension(RegimeDimensionName.VOLATILITY, "HIGH", 0.71),
            RegimeDimension(RegimeDimensionName.FOREIGN_FLOW, "POSITIVE", 0.77),
        ),
        classifier_version="regime-v1",
        feature_snapshot_id="FS-001",
        confidence=0.79,
    )

    assert regime.classifier_version == "regime-v1"
    assert regime.dimensions[0].label == "SIDEWAYS"


def test_market_regime_rejects_duplicate_dimension():
    with pytest.raises(ValueError, match="must be unique"):
        MarketRegime(
            regime_id="REG-DUP",
            as_of=ts(10),
            dimensions=(
                RegimeDimension(RegimeDimensionName.TREND, "SIDEWAYS"),
                RegimeDimension(RegimeDimensionName.TREND, "BULL"),
            ),
            classifier_version="v1",
            feature_snapshot_id="FS-001",
        )


def test_personal_learning_requires_population_scope_and_preserves_contradictions():
    learning = Learning(
        learning_id="LRN-001",
        statement="Short PUT PETR4 had better observed outcomes in similar regimes.",
        status=LearningStatus.ACTIVE,
        learning_scope=LearningScope.PERSONAL_EXPERIENCE,
        population_scope="user historical PETR4 short-put operations",
        first_observed_at=ts(1),
        last_updated_at=ts(20),
        subject_ids=("B3-PETR4",),
        strategy_type="SHORT_PUT",
        regime_ids=("REG-001",),
        sample_size=20,
        recent_sample_size=6,
        win_rate=0.75,
        confidence=0.68,
        evidence_links=(
            LearningEvidenceLink(
                evidence_id="EV-001",
                direction=EvidenceDirection.SUPPORTS,
                operation_id="OP-001",
                observed_at=ts(20),
            ),
            LearningEvidenceLink(
                evidence_id="EV-002",
                direction=EvidenceDirection.CONTRADICTS,
                operation_id="OP-002",
                observed_at=ts(20),
            ),
        ),
        selection_bias_warning="Operations were selected by the investor.",
    )

    assert learning.sample_size == 20
    assert {link.direction for link in learning.evidence_links} == {
        EvidenceDirection.SUPPORTS,
        EvidenceDirection.CONTRADICTS,
    }


def test_personal_learning_without_population_scope_is_rejected():
    with pytest.raises(ValueError, match="requires population_scope"):
        Learning(
            learning_id="LRN-002",
            statement="Observed pattern.",
            status=LearningStatus.CANDIDATE,
            learning_scope=LearningScope.PERSONAL_EXPERIENCE,
            first_observed_at=ts(1),
            last_updated_at=ts(2),
        )


def test_learning_lifecycle_transition_is_explicit():
    transition = LearningLifecycleTransition(
        learning_id="LRN-001",
        from_status=LearningStatus.ACTIVE,
        to_status=LearningStatus.WEAKENING,
        changed_at=ts(25),
        reason="Recent contradictory outcomes reduced confidence.",
        evidence_refs=("OP-021", "OP-022"),
    )

    assert transition.to_status == LearningStatus.WEAKENING


def test_experience_retrieval_exposes_component_scores():
    result = ExperienceRetrievalResult(
        query_id="Q-001",
        as_of=ts(26),
        subject_ids=("B3-PETR4",),
        current_snapshot_id="FS-CURRENT",
        current_regime_id="REG-CURRENT",
        matches=(
            ExperienceMatch(
                reference_id="LRN-001",
                reference_type="LEARNING",
                relevance_score=0.84,
                semantic_score=0.88,
                feature_similarity_score=0.80,
                regime_score=0.91,
                temporal_score=0.70,
                confidence_score=0.73,
            ),
        ),
    )

    assert result.matches[0].regime_score == 0.91


def test_experience_assessment_keeps_support_and_contradiction_separate():
    assessment = ExperienceAssessment(
        historical_similarity=0.82,
        confidence=0.69,
        supporting_learning_ids=("LRN-001",),
        contradicting_learning_ids=("LRN-009",),
        applicable_regime_id="REG-CURRENT",
        limitations=("small recent sample",),
    )

    assert assessment.supporting_learning_ids == ("LRN-001",)
    assert assessment.contradicting_learning_ids == ("LRN-009",)


def test_similarity_scores_must_be_normalized():
    with pytest.raises(ValueError, match="relevance_score must be between 0 and 1"):
        ExperienceMatch(
            reference_id="OP-001",
            reference_type="OPERATION",
            relevance_score=1.1,
        )
