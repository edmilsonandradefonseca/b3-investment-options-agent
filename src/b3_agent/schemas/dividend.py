from dataclasses import dataclass
from datetime import date

from .common import DataRecord


@dataclass(frozen=True)
class DividendRecord(DataRecord):
    payment_type: str
    announcement_date: date | None = None
    ex_date: date | None = None
    record_date: date | None = None
    payment_date: date | None = None
    gross_amount: float | None = None
    net_amount: float | None = None
    currency: str = "BRL"
    reference_period: str | None = None
