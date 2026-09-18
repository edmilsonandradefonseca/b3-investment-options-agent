from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class OptionTransaction:
    """Historical option transaction record; it does not represent current holdings."""

    transaction_id: str
    option_ticker: str
    broker: str
    quantity: float
    average_cost: float | None = None
    total_cost: float | None = None
    as_of: date | datetime | None = None
    source_ref: str = ""

    def __post_init__(self) -> None:
        if not self.transaction_id.strip():
            raise ValueError("transaction_id must be non-empty")
        if not self.option_ticker.strip():
            raise ValueError("option_ticker must be non-empty")
        if self.quantity == 0:
            raise ValueError("quantity must be non-zero")
        if self.average_cost is not None and self.average_cost < 0:
            raise ValueError("average_cost must be non-negative")
        if self.total_cost is not None and self.total_cost == 0:
            raise ValueError("total_cost must be non-zero when provided")
