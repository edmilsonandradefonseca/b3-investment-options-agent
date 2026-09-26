from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OperationStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ASSIGNED = "ASSIGNED"
    EXERCISED = "EXERCISED"
    ROLLED = "ROLLED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class OperationDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    MIXED = "MIXED"


@dataclass(frozen=True)
class Operation:
    """Economic investment operation reconstructed from one or more source transactions."""

    operation_id: str
    strategy_type: str
    underlying_id: str
    opened_at: datetime
    status: OperationStatus

    direction: OperationDirection = OperationDirection.MIXED
    quantity: float | None = None
    capital_committed: float | None = None
    closed_at: datetime | None = None

    instrument_ids: tuple[str, ...] = ()
    option_leg_ids: tuple[str, ...] = ()
    source_transaction_ids: tuple[str, ...] = ()
    broker_refs: tuple[str, ...] = ()

    entry_snapshot_id: str | None = None
    exit_snapshot_id: str | None = None
    outcome_id: str | None = None

    predecessor_operation_ids: tuple[str, ...] = ()
    successor_operation_ids: tuple[str, ...] = ()

    source_refs: tuple[str, ...] = ()
    provenance: str = ""
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.operation_id.strip():
            raise ValueError("operation_id must be non-empty")
        if not self.strategy_type.strip():
            raise ValueError("strategy_type must be non-empty")
        if not self.underlying_id.strip():
            raise ValueError("underlying_id must be non-empty")

        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise ValueError("opened_at must be timezone-aware")
        if self.closed_at is not None:
            if self.closed_at.tzinfo is None or self.closed_at.utcoffset() is None:
                raise ValueError("closed_at must be timezone-aware")
            if self.closed_at < self.opened_at:
                raise ValueError("closed_at must not precede opened_at")

        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("quantity must be positive when provided")
        if self.capital_committed is not None and self.capital_committed < 0:
            raise ValueError("capital_committed must be non-negative when provided")

        if self.status == OperationStatus.OPEN and self.closed_at is not None:
            raise ValueError("OPEN operation must not have closed_at")
        if self.status in {
            OperationStatus.CLOSED,
            OperationStatus.ASSIGNED,
            OperationStatus.EXERCISED,
            OperationStatus.ROLLED,
        } and self.closed_at is None:
            raise ValueError(f"{self.status.value} operation requires closed_at")

        if self.operation_id in self.predecessor_operation_ids:
            raise ValueError("operation cannot be its own predecessor")
        if self.operation_id in self.successor_operation_ids:
            raise ValueError("operation cannot be its own successor")

        _validate_non_empty_values("instrument_ids", self.instrument_ids)
        _validate_non_empty_values("option_leg_ids", self.option_leg_ids)
        _validate_non_empty_values("source_transaction_ids", self.source_transaction_ids)
        _validate_non_empty_values("broker_refs", self.broker_refs)
        _validate_non_empty_values("predecessor_operation_ids", self.predecessor_operation_ids)
        _validate_non_empty_values("successor_operation_ids", self.successor_operation_ids)
        _validate_non_empty_values("source_refs", self.source_refs)


def _validate_non_empty_values(field_name: str, values: tuple[str, ...]) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} must not contain empty values")
