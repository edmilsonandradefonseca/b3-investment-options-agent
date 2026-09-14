from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.quant import QuantFeatures
def _prices(records: Sequence[StockMarketData]) -> list[float]:
    return [
        r.adjusted_close if r.adjusted_close is not None else r.close
        for r in records
    ]
def _sma(values: Sequence[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window
def _returns(values: Sequence[float]) -> list[float]:
    if len(values) < 2:
        return []
    return [
        values[i] / values[i - 1] - 1.0
        for i in range(1, len(values))
        if values[i - 1] > 0
    ]
def _log_returns(values: Sequence[float]) -> list[float]:
    if len(values) < 2:
        return []
    return [
        math.log(values[i] / values[i - 1])
        for i in range(1, len(values))
        if values[i - 1] > 0 and values[i] > 0
    ]
def _sample_std(values: Sequence[float]) -> float | None:
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)
def _annualized_volatility(values: Sequence[float], window: int) -> float | None:
    returns = _log_returns(values)
    if len(returns) < window:
        return None
    volatility = _sample_std(returns[-window:])
    if volatility is None:
        return None
    return volatility * math.sqrt(252.0)
def _max_drawdown(values: Sequence[float]) -> float | None:
    if not values:
        return None
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = value / peak - 1.0
            max_drawdown = min(max_drawdown, drawdown)
    return max_drawdown
def _completeness(records: Sequence[StockMarketData]) -> float:
    if not records:
        return 0.0
    required = 0
    available = 0
    for record in records:
        required += 5
        available += int(record.open is not None)
        available += int(record.high is not None)
        available += int(record.low is not None)
        available += int(record.close is not None)
        available += int(record.volume is not None)
    return available / required if required else 0.0
def _ema(values: Sequence[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    multiplier = 2.0 / (period + 1)
    ema_values = [sum(values[:period]) / period]
    for value in values[period:]:
        ema_values.append(
            (value - ema_values[-1]) * multiplier + ema_values[-1]
        )
    return ema_values
def _rsi(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(changes)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))
def _macd(
    values: Sequence[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[float | None, float | None, float | None]:
    if len(values) < slow_period:
        return None, None, None
    fast = _ema(values, fast_period)
    slow = _ema(values, slow_period)
    offset = slow_period - fast_period
    macd_values = [
        fast[i + offset] - slow[i]
        for i in range(len(slow))
    ]
    if len(macd_values) < signal_period:
        return None, None, None
    signal_values = _ema(macd_values, signal_period)
    if not signal_values:
        return None, None, None
    macd_value = macd_values[-1]
    signal_value = signal_values[-1]
    histogram = macd_value - signal_value
    return macd_value, signal_value, histogram
def _aligned_returns(
    asset_records: Sequence[StockMarketData],
    benchmark_records: Sequence[StockMarketData],
) -> tuple[list[float], list[float]]:
    asset = {
        r.observation_timestamp: (
            r.adjusted_close if r.adjusted_close is not None else r.close
        )
        for r in asset_records
    }
    benchmark = {
        r.observation_timestamp: (
            r.adjusted_close if r.adjusted_close is not None else r.close
        )
        for r in benchmark_records
    }
    timestamps = sorted(set(asset) & set(benchmark))
    asset_prices = [asset[t] for t in timestamps]
    benchmark_prices = [benchmark[t] for t in timestamps]
    return _returns(asset_prices), _returns(benchmark_prices)
def _correlation(
    asset_returns: Sequence[float],
    benchmark_returns: Sequence[float],
) -> float | None:
    if len(asset_returns) != len(benchmark_returns) or len(asset_returns) < 2:
        return None
    asset_mean = sum(asset_returns) / len(asset_returns)
    benchmark_mean = sum(benchmark_returns) / len(benchmark_returns)
    asset_dev = [x - asset_mean for x in asset_returns]
    benchmark_dev = [x - benchmark_mean for x in benchmark_returns]
    numerator = sum(
        a * b for a, b in zip(asset_dev, benchmark_dev)
    )
    asset_ss = sum(x * x for x in asset_dev)
    benchmark_ss = sum(x * x for x in benchmark_dev)
    denominator = math.sqrt(asset_ss * benchmark_ss)
    if denominator == 0:
        return None
    return numerator / denominator
def _beta(
    asset_returns: Sequence[float],
    benchmark_returns: Sequence[float],
) -> float | None:
    if len(asset_returns) != len(benchmark_returns) or len(asset_returns) < 2:
        return None
    benchmark_mean = sum(benchmark_returns) / len(benchmark_returns)
    asset_mean = sum(asset_returns) / len(asset_returns)
    covariance = sum(
        (a - asset_mean) * (b - benchmark_mean)
        for a, b in zip(asset_returns, benchmark_returns)
    )
    benchmark_variance = sum(
        (b - benchmark_mean) ** 2
        for b in benchmark_returns
    )
    if benchmark_variance == 0:
        return None
    return covariance / benchmark_variance
    return covariance / benchmark_variance
def compute_quant_features(
    records: Sequence[StockMarketData],
    *,
    as_of: datetime | None = None,
    benchmark_records: Sequence[StockMarketData] | None = None,
) -> QuantFeatures:
    if not records:
        raise ValueError("records must not be empty")
    ordered = sorted(
        records,
        key=lambda record: record.observation_timestamp,
    )
    prices = _prices(ordered)
    returns = _returns(prices)
    latest = ordered[-1]
    latest_return = None
    latest_log_return = None
    if len(ordered) >= 2:
        previous = ordered[-2]
        previous_price = (
            previous.adjusted_close
            if previous.adjusted_close is not None
            else previous.close
        )
        current_price = (
            latest.adjusted_close
            if latest.adjusted_close is not None
            else latest.close
        )
        time_delta = (
            latest.observation_timestamp
            - previous.observation_timestamp
        )
        if (
            previous_price > 0
            and current_price > 0
            and time_delta.days <= 1
        ):
            latest_return = (current_price / previous_price) - 1.0
            latest_log_return = math.log(current_price / previous_price)
    rsi_value = _rsi(prices, 14)
    beta_value = None
    correlation_value = None
    if benchmark_records is not None:
        asset_returns, benchmark_returns = _aligned_returns(
            ordered,
            benchmark_records,
        )
        beta_value = _beta(asset_returns, benchmark_returns)
        correlation_value = _correlation(
            asset_returns,
            benchmark_returns,
        )
    beta_value = None
    correlation_value = None
    if benchmark_records is not None:
        asset_returns, benchmark_returns = _aligned_returns(
            ordered,
            benchmark_records,
        )
        beta_value = _beta(asset_returns, benchmark_returns)
        correlation_value = _correlation(
            asset_returns,
            benchmark_returns,
        )
    macd_value, macd_signal, macd_histogram = _macd(prices)
    average_volume = (
        sum(r.volume for r in ordered[-20:]) / min(20, len(ordered))
    )
    average_dollar_volume = (
        sum(
            (
                r.adjusted_close
                if r.adjusted_close is not None
                else r.close
            ) * r.volume
            for r in ordered[-20:]
        )
        / min(20, len(ordered))
    )
    return QuantFeatures(
        instrument_id=latest.instrument_id,
        ticker=latest.ticker,
        as_of=as_of or latest.observation_timestamp,
        return_1d=latest_return,
        log_return_1d=latest_log_return,
        volatility_20d=_annualized_volatility(prices, 20),
        volatility_60d=_annualized_volatility(prices, 60),
        sma_20=_sma(prices, 20),
        sma_50=_sma(prices, 50),
        sma_200=_sma(prices, 200),
        max_drawdown=_max_drawdown(prices),
        rsi_14=rsi_value,
        macd=macd_value,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        beta=beta_value,
        correlation=correlation_value,
        average_volume_20d=average_volume,
        average_dollar_volume_20d=average_dollar_volume,
        data_points=len(ordered),
        completeness_score=_completeness(ordered),
        quality_status="VALID",
    )
