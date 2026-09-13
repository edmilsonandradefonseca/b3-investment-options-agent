from dataclasses import dataclass
from datetime import date, datetime

from .common import DataRecord


@dataclass(frozen=True)
class StockFundamental(DataRecord):
    metric: str
    value: float
    period_start: date | None = None
    period_end: date | None = None
    report_date: date | None = None
    unit: str | None = None
