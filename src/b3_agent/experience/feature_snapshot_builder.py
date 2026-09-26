from __future__ import annotations

from hashlib import sha256
from collections.abc import Iterable

from b3_agent.quant_engine import compute_quant_features
from b3_agent.schemas.feature_snapshot import (
    FeatureDomain,
    FeatureSnapshot,
    FeatureValue,
)
from b3_agent.schemas.market import StockMarketData


class FeatureSnapshotBuilder:
    """Build compact immutable PIT snapshots from already normalized records."""

    def build(
        self,
        *,
        subject_id: str,
        as_of,
        market_records: Iterable[StockMarketData] = (),
        benchmark_records: Iterable[StockMarketData] = (),
        extra_features: Iterable[FeatureValue] = (),
        operation_id: str | None = None,
        regime_id: str | None = None,
        event_refs: tuple[str, ...] = (),
        source_refs: tuple[str, ...] = (),
    ) -> FeatureSnapshot:
        eligible_market = tuple(
            sorted(
                (
                    record
                    for record in market_records
                    if record.observation_timestamp <= as_of
                    and record.available_timestamp <= as_of
                ),
                key=lambda record: record.observation_timestamp,
            )
        )
        eligible_benchmark = tuple(
            sorted(
                (
                    record
                    for record in benchmark_records
                    if record.observation_timestamp <= as_of
                    and record.available_timestamp <= as_of
                ),
                key=lambda record: record.observation_timestamp,
            )
        )

        features: list[FeatureValue] = list(extra_features)
        if any(feature.available_at > as_of for feature in features):
            raise ValueError("extra feature available_at must not exceed snapshot as_of")

        if eligible_market:
            latest = eligible_market[-1]
            features.extend(
                (
                    FeatureValue(
                        name="close",
                        value=latest.adjusted_close
                        if latest.adjusted_close is not None
                        else latest.close,
                        domain=FeatureDomain.MARKET,
                        available_at=latest.available_timestamp,
                        unit=latest.currency,
                        source_ref=latest.source_record_id or latest.source,
                    ),
                    FeatureValue(
                        name="volume",
                        value=latest.volume,
                        domain=FeatureDomain.MARKET,
                        available_at=latest.available_timestamp,
                        source_ref=latest.source_record_id or latest.source,
                    ),
                )
            )

            quant = compute_quant_features(
                eligible_market,
                as_of=as_of,
                benchmark_records=eligible_benchmark or None,
            )
            quant_available_at = max(
                record.available_timestamp for record in eligible_market
            )
            for name in (
                "return_1d",
                "volatility_20d",
                "volatility_60d",
                "sma_20",
                "sma_50",
                "sma_200",
                "rsi_14",
                "macd",
                "macd_signal",
                "macd_histogram",
                "max_drawdown",
                "beta",
                "correlation",
                "average_volume_20d",
                "average_dollar_volume_20d",
                "completeness_score",
            ):
                value = getattr(quant, name)
                if value is None:
                    continue
                features.append(
                    FeatureValue(
                        name=name,
                        value=value,
                        domain=FeatureDomain.MARKET,
                        available_at=quant_available_at,
                        source_ref=f"quant:{quant.ticker}",
                    )
                )

        digest = sha256(
            f"{subject_id}|{as_of.isoformat()}|{operation_id or ''}".encode("utf-8")
        ).hexdigest()[:16]
        combined_sources = tuple(
            dict.fromkeys(
                [
                    *source_refs,
                    *(
                        record.source_record_id or record.source
                        for record in eligible_market
                    ),
                ]
            )
        )

        return FeatureSnapshot(
            snapshot_id=f"FS-{digest}",
            subject_id=subject_id,
            as_of=as_of,
            features=tuple(features),
            operation_id=operation_id,
            regime_id=regime_id,
            event_refs=event_refs,
            source_refs=combined_sources,
            quality_status="VALID" if features else "WARNING",
            provenance="feature_snapshot_builder:v1",
            schema_version="1.0",
        )
