from dataclasses import dataclass

from .common import DataRecord


@dataclass(frozen=True)
class MacroObservation(DataRecord):
    indicator: str
    value: float
    unit: str
    reference_period: str | None = None
