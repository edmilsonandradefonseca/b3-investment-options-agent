from dataclasses import dataclass


@dataclass(frozen=True)
class QuantFeatures:
    instrument_id: str
    ticker: str

    as_of: object

    return_1d: float | None = None
    log_return_1d: float | None = None

    volatility_20d: float | None = None
    volatility_60d: float | None = None

    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None

    rsi_14: float | None = None

    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None

    max_drawdown: float | None = None

    beta: float | None = None
    correlation: float | None = None
    correlation: float | None = None

    average_volume_20d: float | None = None
    average_dollar_volume_20d: float | None = None

    data_points: int = 0
    completeness_score: float = 0.0
    quality_status: str = "VALID"
