from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Transaction:
    """Permanent user-entered execution ledger record."""

    transaction_id: str
    executed_at: datetime
    action: str
    instrument_type: str
    ticker: str
    quantity: float
    price: float
    broker: str = ""
    source_ref: str = "desktop:manual"

    def __post_init__(self) -> None:
        if not self.transaction_id.strip():
            raise ValueError("transaction_id must be non-empty")
        if self.executed_at.tzinfo is None:
            raise ValueError("executed_at must be timezone-aware")
        if self.action not in {"BUY", "SELL"}:
            raise ValueError("action must be BUY or SELL")
        if self.instrument_type not in {"STOCK", "OPTION"}:
            raise ValueError("instrument_type must be STOCK or OPTION")
        if not self.ticker.strip():
            raise ValueError("ticker must be non-empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.price < 0:
            raise ValueError("price must be non-negative")

    @property
    def signed_quantity(self) -> float:
        return self.quantity if self.action == "BUY" else -self.quantity
