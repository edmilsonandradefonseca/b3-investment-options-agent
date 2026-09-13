from dataclasses import dataclass
from datetime import date

from .common import DataRecord


@dataclass(frozen=True)
class FlowData(DataRecord):
    investor_type: str
    market_segment: str
    buy_quantity: float | None = None
    sell_quantity: float | None = None
    buy_financial_value: float | None = None
    sell_financial_value: float | None = None
    net_quantity: float | None = None
    net_financial_value: float | None = None
    observation_date: date | None = None
