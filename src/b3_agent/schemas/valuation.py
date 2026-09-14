from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class ValuationInputs:
    """Normalized, deterministic inputs consumed by a valuation method."""

    instrument_id: str
    ticker: str
    as_of: date | datetime
    method: str

    # Company metrics. Methods should use only the fields they require.
    price: float | None = None
    earnings_per_share: float | None = None
    book_value_per_share: float | None = None
    ebitda: float | None = None
    enterprise_value: float | None = None
    free_cash_flow: float | None = None
    revenue: float | None = None
    roe: float | None = None
    dividend_per_share: float | None = None

    # Method/scenario assumptions. Kept explicit and auditable.
    assumptions: dict[str, Any] = field(default_factory=dict)
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"


@dataclass(frozen=True)
class ValuationRange:
    """Bear/Base/Bull valuation output plus the investment price policy."""

    instrument_id: str
    ticker: str
    as_of: date | datetime
    method: str

    bear_value: float
    base_value: float
    bull_value: float

    accumulation_price: float | None = None
    reduce_price: float | None = None
    sell_price: float | None = None
    margin_of_safety: float | None = None

    assumptions: dict[str, Any] = field(default_factory=dict)
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"

    def __post_init__(self) -> None:
        if self.bear_value > self.base_value or self.base_value > self.bull_value:
            raise ValueError("Valuation values must satisfy bear <= base <= bull")

        prices = (
            self.accumulation_price,
            self.reduce_price,
            self.sell_price,
        )
        if any(value is not None and value < 0 for value in prices):
            raise ValueError("Investment policy prices cannot be negative")
