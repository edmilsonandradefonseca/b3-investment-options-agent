from dataclasses import dataclass
from datetime import datetime

from .common import DataRecord


@dataclass(frozen=True)
class StockMarketData(DataRecord):
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float | None = None
    currency: str = "BRL"
