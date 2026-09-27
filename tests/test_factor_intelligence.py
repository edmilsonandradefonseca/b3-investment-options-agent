from datetime import datetime, timedelta, timezone
from b3_agent.factor_intelligence import FactorIntelligenceEngine
from b3_agent.schemas.factor import FactorObservation


def _series(sign=1.0, n=60):
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    return tuple(FactorObservation(start+timedelta(days=i), float(i), sign*(float(i)/1000.0)) for i in range(n))


def test_factor_engine_uses_holdout_and_multiple_testing_control():
    study=FactorIntelligenceEngine().analyze({"momentum":_series(1),"inverse":_series(-1)},as_of=datetime(2026,9,27,tzinfo=timezone.utc))
    assert study.correction_method == "BENJAMINI_HOCHBERG"
    assert len(study.results)==2
    for result in study.results:
        assert result.train_size == 42
        assert result.holdout_size == 18
        assert result.direction_stable is True
        assert result.statistically_significant is True
        assert result.adjusted_p_value == 0.0
        assert result.interpretation == "association_only_no_causal_claim"


def test_factor_engine_rejects_small_sample_as_validated_evidence():
    study=FactorIntelligenceEngine().analyze({"tiny":_series(1,10)},as_of=datetime(2026,9,27,tzinfo=timezone.utc))
    result=study.results[0]
    assert result.quality_status == "WARNING"
    assert result.statistically_significant is False
    assert result.p_value is None


def test_factor_walk_forward_requires_persistent_direction():
    result=FactorIntelligenceEngine().walk_forward("momentum",_series(1,70),as_of=datetime(2026,9,27,tzinfo=timezone.utc),train_size=30,test_size=10)
    assert len(result.folds)==4
    assert result.stable_fold_ratio == 1.0
    assert result.median_test_correlation is not None
    assert result.median_test_correlation > .99
    assert result.interpretation == "association_only_no_causal_claim"
