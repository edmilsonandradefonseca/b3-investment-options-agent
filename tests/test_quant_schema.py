from datetime import datetime, timezone

from b3_agent.schemas.quant import QuantFeatures


def test_quant_features_contract():
    features = QuantFeatures(
        instrument_id="ITUB4",
        ticker="ITUB4",
        as_of=datetime(2026, 9, 11, tzinfo=timezone.utc),
        return_1d=0.01,
        log_return_1d=0.00995,
        volatility_20d=0.25,
        sma_20=42.0,
        rsi_14=55.0,
        data_points=100,
        completeness_score=1.0,
    )

    assert features.ticker == "ITUB4"
    assert features.return_1d == 0.01
    assert features.data_points == 100
    assert features.completeness_score == 1.0


def test_quant_features_defaults():
    features = QuantFeatures(
        instrument_id="ITUB4",
        ticker="ITUB4",
        as_of=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )

    assert features.return_1d is None
    assert features.volatility_20d is None
    assert features.sma_200 is None
    assert features.rsi_14 is None
    assert features.data_points == 0
    assert features.completeness_score == 0.0
    assert features.quality_status == "VALID"
