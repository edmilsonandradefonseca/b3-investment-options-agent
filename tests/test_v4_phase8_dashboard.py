from datetime import datetime, timedelta, timezone

from b3_agent.change_detection import AnalysisChangeDetector
from b3_agent.dashboard_v4 import DashboardV4Presenter
from b3_agent.schemas.analysis_run import AnalysisRun
from b3_agent.schemas.experience import ExperienceAssessment, ExperienceMatch, ExperienceRetrievalResult
from b3_agent.schemas.learning import Learning, LearningScope, LearningStatus
from b3_agent.schemas.market_regime import MarketRegime, RegimeDimension, RegimeDimensionName


BASE = datetime(2026, 9, 25, 15, 0, tzinfo=timezone.utc)


def test_change_detector_reports_material_analysis_run_changes():
    previous = AnalysisRun(
        analysis_id="AN-1",
        as_of=BASE,
        request_scope="PETR4",
        feature_snapshot_id="FS-1",
        market_regime_id="REG-SIDEWAYS",
        relevant_learning_ids=("LRN-1",),
        opportunity_refs=("OPP-1",),
        risk_refs=("RISK-1",),
    )
    current = AnalysisRun(
        analysis_id="AN-2",
        as_of=BASE + timedelta(days=1),
        request_scope="PETR4",
        feature_snapshot_id="FS-2",
        market_regime_id="REG-BULL",
        relevant_learning_ids=("LRN-1", "LRN-2"),
        opportunity_refs=("OPP-2",),
        risk_refs=("RISK-1",),
    )

    changes = AnalysisChangeDetector().compare(previous, current)

    fields = {item.field for item in changes.changes}
    assert "feature_snapshot_id" in fields
    assert "market_regime_id" in fields
    assert "relevant_learning_ids" in fields
    assert "opportunity_refs" in fields
    assert "risk_refs" not in fields


def test_dashboard_presenter_exposes_v4_learning_regime_and_similarity_without_recalculation():
    regime = MarketRegime(
        regime_id="REG-1",
        as_of=BASE,
        dimensions=(
            RegimeDimension(RegimeDimensionName.TREND, "SIDEWAYS"),
            RegimeDimension(RegimeDimensionName.VOLATILITY, "HIGH"),
        ),
        classifier_version="regime-v1",
        feature_snapshot_id="FS-1",
        confidence=0.8,
    )
    learning = Learning(
        learning_id="LRN-1",
        statement="Observed favorable personal outcomes.",
        status=LearningStatus.ACTIVE,
        learning_scope=LearningScope.PERSONAL_EXPERIENCE,
        first_observed_at=BASE - timedelta(days=30),
        last_updated_at=BASE,
        subject_ids=("B3-PETR4",),
        sample_size=12,
        recent_sample_size=5,
        win_rate=0.75,
        confidence=0.7,
        population_scope="user PETR4 operations",
        selection_bias_warning="Selected personal operations.",
    )
    retrieval = ExperienceRetrievalResult(
        query_id="Q-1",
        as_of=BASE,
        subject_ids=("B3-PETR4",),
        current_snapshot_id="FS-1",
        current_regime_id="REG-1",
        matches=(
            ExperienceMatch(
                reference_id="EXP-1",
                reference_type="EXPERIENCE",
                relevance_score=0.82,
                regime_score=1.0,
                temporal_score=0.7,
            ),
        ),
    )
    assessment = ExperienceAssessment(
        historical_similarity=0.82,
        confidence=0.7,
        supporting_learning_ids=("LRN-1",),
        applicable_regime_id="REG-1",
        limitations=("small sample",),
    )

    view = DashboardV4Presenter().build(
        market_regime=regime,
        experience_assessment=assessment,
        historical_similarity=retrieval,
        learnings=(learning,),
    ).as_dict()

    assert view["market_regime"]["regime_id"] == "REG-1"
    assert view["experience_assessment"]["historical_similarity"] == 0.82
    assert view["historical_similarity"]["matches"][0]["regime_score"] == 1.0
    assert view["learnings"][0]["learning_id"] == "LRN-1"
    assert view["learnings"][0]["supporting_evidence"] == 0
    assert view["learnings"][0]["selection_bias_warning"] is not None


def test_dashboard_presenter_returns_none_instead_of_fabricating_missing_sections():
    view = DashboardV4Presenter().build().as_dict()

    assert view["market_regime"] is None
    assert view["experience_assessment"] is None
    assert view["historical_similarity"] is None
    assert view["learnings"] == []
    assert view["stress"] is None
    assert view["strategy_comparison"] is None
    assert view["changes"] is None
