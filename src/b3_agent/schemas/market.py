from dataclasses import dataclass

from .common import DataRecord


@dataclass(frozen=True)
class StockMarketData(DataRecord):
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None = None
    vwap: float | None = None
    currency: str = "BRL"
