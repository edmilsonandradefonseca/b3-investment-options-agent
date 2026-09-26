from __future__ import annotations

from hashlib import sha256

from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.market_regime import (
    MarketRegime,
    RegimeDimension,
    RegimeDimensionName,
)


class MarketRegimeEngine:
    """Deterministic, explainable V1 regime classifier over a FeatureSnapshot."""

    TOTAL_DIMENSIONS = 6

    def classify(self, snapshot: FeatureSnapshot) -> MarketRegime:
        values = {feature.name: feature.value for feature in snapshot.features}
        dimensions: list[RegimeDimension] = []

        close = _number(values.get("close"))
        sma20 = _number(values.get("sma_20"))
        sma50 = _number(values.get("sma_50"))
        if close is not None and sma20 is not None and sma50 is not None:
            if close > sma20 > sma50:
                label = "BULL"
            elif close < sma20 < sma50:
                label = "BEAR"
            else:
                label = "SIDEWAYS"
            dimensions.append(RegimeDimension(RegimeDimensionName.TREND, label))

        vol20 = _number(values.get("volatility_20d"))
        if vol20 is not None:
            if vol20 >= 0.60:
                label = "STRESS"
            elif vol20 >= 0.40:
                label = "HIGH"
            elif vol20 < 0.20:
                label = "LOW"
            else:
                label = "NORMAL"
            dimensions.append(RegimeDimension(RegimeDimensionName.VOLATILITY, label))

        drawdown = _number(values.get("max_drawdown"))
        if drawdown is not None or close is not None:
            trend_label = _label(dimensions, RegimeDimensionName.TREND)
            volatility_label = _label(dimensions, RegimeDimensionName.VOLATILITY)
            if drawdown is not None and drawdown <= -0.15:
                risk_label = "RISK_OFF"
            elif trend_label == "BULL" and volatility_label not in {"HIGH", "STRESS"}:
                risk_label = "RISK_ON"
            else:
                risk_label = "NEUTRAL"
            dimensions.append(
                RegimeDimension(RegimeDimensionName.RISK_APPETITE, risk_label)
            )

        rate_change = _number(values.get("di_change_bps_20d"))
        if rate_change is not None:
            if rate_change >= 25.0:
                rate_label = "RISING"
            elif rate_change <= -25.0:
                rate_label = "FALLING"
            else:
                rate_label = "STABLE"
            dimensions.append(RegimeDimension(RegimeDimensionName.RATES, rate_label))

        foreign_flow = _number(values.get("foreign_flow_5d"))
        if foreign_flow is not None:
            if foreign_flow > 0:
                flow_label = "POSITIVE"
            elif foreign_flow < 0:
                flow_label = "NEGATIVE"
            else:
                flow_label = "NEUTRAL"
            dimensions.append(
                RegimeDimension(RegimeDimensionName.FOREIGN_FLOW, flow_label)
            )

        commodity_return = _number(values.get("commodity_return_20d"))
        if commodity_return is not None:
            if commodity_return > 0.03:
                commodity_label = "UP"
            elif commodity_return < -0.03:
                commodity_label = "DOWN"
            else:
                commodity_label = "FLAT"
            dimensions.append(
                RegimeDimension(RegimeDimensionName.COMMODITY, commodity_label)
            )

        if not dimensions:
            raise ValueError("snapshot does not contain enough features for regime classification")

        signature = "|".join(
            f"{dimension.name.value}:{dimension.label}" for dimension in dimensions
        )
        digest = sha256(
            f"{snapshot.snapshot_id}|{signature}".encode("utf-8")
        ).hexdigest()[:16]

        return MarketRegime(
            regime_id=f"REG-{digest}",
            as_of=snapshot.as_of,
            dimensions=tuple(dimensions),
            classifier_version="regime-v1",
            feature_snapshot_id=snapshot.snapshot_id,
            confidence=len(dimensions) / self.TOTAL_DIMENSIONS,
            valid_from=snapshot.as_of,
            source_refs=snapshot.source_refs,
            provenance="market_regime_engine:v1",
            schema_version="1.0",
        )


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _label(
    dimensions: list[RegimeDimension],
    name: RegimeDimensionName,
) -> str | None:
    for dimension in dimensions:
        if dimension.name == name:
            return dimension.label
    return None
