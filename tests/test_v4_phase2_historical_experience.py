from datetime import datetime, timedelta, timezone

import pytest

from b3_agent.experience import (
    FeatureSnapshotBuilder,
    MarketRegimeEngine,
    OperationMetadata,
    OperationReconstructionError,
    OperationReconstructor,
    OutcomeEngine,
)
from b3_agent.schemas.feature_snapshot import FeatureDomain, FeatureValue
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.operation import OperationStatus
from b3_agent.schemas.transaction import Transaction


def ts(day: int, hour: int = 15) -> datetime:
    return datetime(2026, 9, day, hour, 0, tzinfo=timezone.utc)


def tx(
    transaction_id: str,
    day: int,
    action: str,
    quantity: float,
    price: float,
    *,
    ticker: str = "PETR4",
    instrument_type: str = "STOCK",
) -> Transaction:
    return Transaction(
        transaction_id=transaction_id,
        executed_at=ts(day),
        action=action,
        instrument_type=instrument_type,
        ticker=ticker,
        quantity=quantity,
        price=price,
        broker="BTG",
        source_ref=f"broker:{transaction_id}",
    )


def market_record(day: int, close: float, *, available_day: int | None = None) -> StockMarketData:
    available_day = available_day or day
    observed = ts(day, 18)
    available = ts(available_day, 20)
    return StockMarketData(
        instrument_id="B3-PETR4",
        ticker="PETR4",
        observation_timestamp=observed,
        available_timestamp=available,
        source="test",
        ingested_at=available,
        source_record_id=f"PETR4:{day}",
        open=close - 0.5,
        high=close + 0.5,
        low=close - 1.0,
        close=close,
        volume=1_000_000 + day,
    )


def test_operation_reconstruction_closes_round_trip_and_is_deterministic():
    transactions = (
        tx("T1", 1, "BUY", 100, 30.0),
        tx("T2", 10, "SELL", 100, 32.0),
    )

    engine = OperationReconstructor()
    first = engine.reconstruct(transactions)
    second = engine.reconstruct(reversed(transactions))

    assert len(first) == 1
    assert first == second
    operation = first[0]
    assert operation.status == OperationStatus.CLOSED
    assert operation.strategy_type == "LONG_STOCK"
    assert operation.source_transaction_ids == ("T1", "T2")
    assert operation.closed_at == ts(10)


def test_operation_reconstruction_supports_option_metadata():
    transactions = (
        tx("O1", 2, "SELL", 100, 2.0, ticker="PETRV350", instrument_type="OPTION"),
        tx("O2", 15, "BUY", 100, 0.8, ticker="PETRV350", instrument_type="OPTION"),
    )

    operations = OperationReconstructor().reconstruct(
        transactions,
        metadata_by_ticker={
            "PETRV350": OperationMetadata(
                underlying_id="B3-PETR4",
                strategy_type="SHORT_PUT",
                instrument_ids=("B3-PETR4", "PETRV350"),
                option_leg_ids=("PETRV350",),
            )
        },
    )

    assert operations[0].underlying_id == "B3-PETR4"
    assert operations[0].strategy_type == "SHORT_PUT"
    assert operations[0].option_leg_ids == ("PETRV350",)


def test_operation_reconstruction_rejects_unsplit_position_flip():
    transactions = (
        tx("T1", 1, "BUY", 100, 30.0),
        tx("T2", 2, "SELL", 150, 31.0),
    )

    with pytest.raises(OperationReconstructionError, match="crosses position through zero"):
        OperationReconstructor().reconstruct(transactions)


def test_feature_snapshot_builder_filters_unavailable_future_market_data():
    records = [
        market_record(day, 30.0 + day * 0.2)
        for day in range(1, 30)
    ]
    records.append(market_record(30, 50.0, available_day=30))

    snapshot = FeatureSnapshotBuilder().build(
        subject_id="B3-PETR4",
        as_of=ts(30, 19),
        market_records=records,
        operation_id="OP-1",
        extra_features=(
            FeatureValue(
                name="foreign_flow_5d",
                value=500.0,
                domain=FeatureDomain.FLOW,
                available_at=ts(30, 18),
                unit="BRL_mn",
            ),
        ),
    )

    values = {feature.name: feature.value for feature in snapshot.features}
    assert values["close"] == pytest.approx(35.8)
    assert "sma_20" in values
    assert values["foreign_flow_5d"] == 500.0
    assert "PETR4:30" not in snapshot.source_refs


def test_feature_snapshot_builder_rejects_future_extra_feature():
    with pytest.raises(ValueError, match="extra feature available_at"):
        FeatureSnapshotBuilder().build(
            subject_id="B3-PETR4",
            as_of=ts(10),
            extra_features=(
                FeatureValue(
                    name="future",
                    value=1.0,
                    domain=FeatureDomain.EVENT,
                    available_at=ts(11),
                ),
            ),
        )


def test_market_regime_reconstruction_is_deterministic():
    snapshot = FeatureSnapshotBuilder().build(
        subject_id="B3-PETR4",
        as_of=ts(20),
        extra_features=(
            FeatureValue("close", 40.0, FeatureDomain.MARKET, ts(20, 14)),
            FeatureValue("sma_20", 39.0, FeatureDomain.MARKET, ts(20, 14)),
            FeatureValue("sma_50", 38.0, FeatureDomain.MARKET, ts(20, 14)),
            FeatureValue("volatility_20d", 0.45, FeatureDomain.MARKET, ts(20, 14)),
            FeatureValue("max_drawdown", -0.05, FeatureDomain.MARKET, ts(20, 14)),
            FeatureValue("foreign_flow_5d", 100.0, FeatureDomain.FLOW, ts(20, 14)),
            FeatureValue("di_change_bps_20d", 10.0, FeatureDomain.MACRO, ts(20, 14)),
            FeatureValue("commodity_return_20d", -0.05, FeatureDomain.COMMODITY, ts(20, 14)),
        ),
    )

    first = MarketRegimeEngine().classify(snapshot)
    second = MarketRegimeEngine().classify(snapshot)
    labels = {dimension.name.value: dimension.label for dimension in first.dimensions}

    assert first == second
    assert labels["TREND"] == "BULL"
    assert labels["VOLATILITY"] == "HIGH"
    assert labels["FOREIGN_FLOW"] == "POSITIVE"
    assert labels["RATES"] == "STABLE"
    assert labels["COMMODITY"] == "DOWN"


def test_outcome_engine_finalizes_realized_pnl_and_emits_idempotent_event():
    transactions = (
        tx("T1", 1, "BUY", 100, 30.0),
        tx("T2", 10, "SELL", 100, 32.0),
    )
    operation = OperationReconstructor().reconstruct(transactions)[0]

    engine = OutcomeEngine()
    outcome, event = engine.finalize_with_event(operation, transactions)
    outcome2, event2 = engine.finalize_with_event(operation, transactions)

    assert outcome.realized_pnl == pytest.approx(200.0)
    assert outcome.holding_period_days == 9
    assert outcome.operation_id == operation.operation_id
    assert event.operation_id == operation.operation_id
    assert event.idempotency_key == event2.idempotency_key
    assert outcome == outcome2


def test_outcome_engine_does_not_finalize_open_operation():
    operation = OperationReconstructor().reconstruct((tx("T1", 1, "BUY", 100, 30.0),))[0]

    with pytest.raises(ValueError, match="terminal"):
        OutcomeEngine().finalize(operation, (tx("T1", 1, "BUY", 100, 30.0),))


def test_phase2_end_to_end_historical_experience_substrate():
    transactions = (
        tx("T1", 1, "BUY", 100, 30.0),
        tx("T2", 10, "SELL", 100, 32.0),
    )
    operation = OperationReconstructor().reconstruct(transactions)[0]

    market = [market_record(day, 28.0 + day * 0.2) for day in range(1, 11)]
    snapshot = FeatureSnapshotBuilder().build(
        subject_id=operation.underlying_id,
        as_of=operation.opened_at + timedelta(hours=6),
        market_records=market,
        operation_id=operation.operation_id,
        extra_features=(
            FeatureValue(
                "foreign_flow_5d",
                200.0,
                FeatureDomain.FLOW,
                operation.opened_at,
            ),
        ),
    )

    # Ten observations are insufficient for some long-window quant features,
    # but the snapshot remains valid and PIT-bounded.
    assert snapshot.operation_id == operation.operation_id
    assert all(feature.available_at <= snapshot.as_of for feature in snapshot.features)

    # Use a richer explicit snapshot to validate regime reconstruction in the
    # same end-to-end substrate without inventing missing historical features.
    regime_snapshot = FeatureSnapshotBuilder().build(
        subject_id=operation.underlying_id,
        as_of=operation.opened_at + timedelta(hours=6),
        operation_id=operation.operation_id,
        extra_features=(
            FeatureValue("close", 30.0, FeatureDomain.MARKET, operation.opened_at),
            FeatureValue("sma_20", 29.0, FeatureDomain.MARKET, operation.opened_at),
            FeatureValue("sma_50", 28.0, FeatureDomain.MARKET, operation.opened_at),
            FeatureValue("volatility_20d", 0.25, FeatureDomain.MARKET, operation.opened_at),
        ),
    )
    regime = MarketRegimeEngine().classify(regime_snapshot)
    outcome, event = OutcomeEngine().finalize_with_event(operation, transactions)

    assert regime.feature_snapshot_id == regime_snapshot.snapshot_id
    assert outcome.operation_id == operation.operation_id
    assert event.outcome_id == outcome.outcome_id
