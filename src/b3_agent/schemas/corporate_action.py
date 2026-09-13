from dataclasses import dataclass
from datetime import date, datetime

from .common import DataRecord


@dataclass(frozen=True)
class CorporateAction(DataRecord):
    action_type: str
    announcement_date: date | None = None
    ex_date: date | None = None
    record_date: date | None = None
    payment_date: date | None = None
    ratio: float | None = None
    amount: float | None = None
    currency: str | None = None
