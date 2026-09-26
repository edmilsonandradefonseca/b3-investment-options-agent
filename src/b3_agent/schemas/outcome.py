from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OutcomeStatus(StrEnum):
    PROVISIONAL = "PROVISIONAL"
    FINAL = "FINAL"
    CORRECTED = "CORRECTED"


@dataclass(frozen=True)
class Outcome:
    """Deterministic realized result of an economic operation."""

    outcome_id: str
    operation_id: str
    finalized_at: datetime
    status: OutcomeStatus

    realized_pnl: float | None = None
    realized_return: float | None = None
    holding_period_days: int | None = None
    max_adverse_excursion: float | None = None
    max_favorable_excursion: float | None = None
    assigned: bool = False
    exercised: bool = False
    exit_reason: str | None = None
    capital_used: float | None = None
    fees: float | None = None
    taxes: float | None = None
    benchmark_return: float | None = None

    quality_status: str = "VALID"
    source_refs: tuple[str, ...] = ()
    provenance: str = ""
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.outcome_id.strip():
            raise ValueError("outcome_id must be non-empty")
        if not self.operation_id.strip():
            raise ValueError("operation_id must be non-empty")
        if self.finalized_at.tzinfo is None or self.finalized_at.utcoffset() is None:
            raise ValueError("finalized_at must be timezone-aware")
        if self.holding_period_days is not None and self.holding_period_days < 0:
            raise ValueError("holding_period_days must be non-negative")
        if self.capital_used is not None and self.capital_used < 0:
            raise ValueError("capital_used must be non-negative")
        if self.fees is not None and self.fees < 0:
            raise ValueError("fees must be non-negative")
        if self.taxes is not None and self.taxes < 0:
            raise ValueError("taxes must be non-negative")
        if any(not value.strip() for value in self.source_refs):
            raise ValueError("source_refs must not contain empty values")
