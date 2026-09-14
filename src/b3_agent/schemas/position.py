from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Position:
    """Normalized portfolio position used by Portfolio Intelligence."""

    position_id: str
    ticker: str
    instrument_type: str
    quantity: float
    average_cost: float | None = None
    strike: float | None = None
    expiration_date: date | None = None
    option_type: str | None = None
    underlying_ticker: str | None = None
    contract_multiplier: float = 1.0
    market_price: float | None = None
    market_value: float | None = None
    source_ref: str = ""

    def __post_init__(self) -> None:
        if not self.position_id.strip():
            raise ValueError("position_id must not be empty")
        if not self.ticker.strip():
            raise ValueError("ticker must not be empty")
        if self.quantity == 0:
            raise ValueError("quantity must not be zero")
        if self.contract_multiplier <= 0:
            raise ValueError("contract_multiplier must be positive")
        if self.average_cost is not None and self.average_cost < 0:
            raise ValueError("average_cost cannot be negative")
        if self.market_price is not None and self.market_price < 0:
            raise ValueError("market_price cannot be negative")
        if self.market_value is not None and self.market_value < 0:
            raise ValueError("market_value cannot be negative")
        if self.instrument_type == "OPTION":
            if self.strike is None or self.expiration_date is None or self.option_type is None:
                raise ValueError("option positions require strike, expiration_date and option_type")


@dataclass(frozen=True)
class PortfolioContext:
    """Deterministic snapshot of normalized positions and exposure metadata."""

    as_of: date
    positions: tuple[Position, ...]
    cash: float = 0.0
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"

    def __post_init__(self) -> None:
        if self.cash < 0:
            raise ValueError("cash cannot be negative")
        if self.quality_status not in {"VALIDATED", "WARNING", "REJECTED"}:
            raise ValueError("invalid quality_status")
