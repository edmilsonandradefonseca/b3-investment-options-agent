from dataclasses import dataclass

from .common import DataRecord


@dataclass(frozen=True)
class YieldCurvePoint(DataRecord):
    curve_code: str
    curve_description: str
    days_calendar: int
    days_business: int
    rate_decimal: float
    vertex: str
