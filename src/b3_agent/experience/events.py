from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from datetime import datetime

from b3_agent.schemas.outcome import Outcome, OutcomeStatus


@dataclass(frozen=True)
class OutcomeFinalized:
    """Idempotent domain event that triggers the V4 POST-OUTCOME workflow."""

    event_id: str
    operation_id: str
    outcome_id: str
    occurred_at: datetime
    idempotency_key: str
    canonical_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must be non-empty")
        if not self.operation_id.strip():
            raise ValueError("operation_id must be non-empty")
        if not self.outcome_id.strip():
            raise ValueError("outcome_id must be non-empty")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key must be non-empty")

    @classmethod
    def from_outcome(cls, outcome: Outcome) -> "OutcomeFinalized":
        if outcome.status not in {OutcomeStatus.FINAL, OutcomeStatus.CORRECTED}:
            raise ValueError("OutcomeFinalized requires FINAL or CORRECTED outcome")

        key = sha256(
            f"{outcome.outcome_id}|{outcome.schema_version}|{outcome.finalized_at.isoformat()}".encode(
                "utf-8"
            )
        ).hexdigest()
        return cls(
            event_id=f"EVT-OUTCOME-{key[:16]}",
            operation_id=outcome.operation_id,
            outcome_id=outcome.outcome_id,
            occurred_at=outcome.finalized_at,
            idempotency_key=key,
            canonical_version=outcome.schema_version,
        )
