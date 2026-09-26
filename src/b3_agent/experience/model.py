from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.market_regime import MarketRegime
from b3_agent.schemas.operation import Operation
from b3_agent.schemas.outcome import Outcome


@dataclass(frozen=True)
class Experience:
    """Canonical in-memory aggregate of an operation, PIT context and realized outcome."""

    experience_id: str
    operation: Operation
    entry_snapshot: FeatureSnapshot
    market_regime: MarketRegime
    outcome: Outcome
    exit_snapshot: FeatureSnapshot | None = None

    def __post_init__(self) -> None:
        if not self.experience_id.strip():
            raise ValueError("experience_id must be non-empty")
        if self.outcome.operation_id != self.operation.operation_id:
            raise ValueError("outcome operation_id must match operation")
        if (
            self.entry_snapshot.operation_id is not None
            and self.entry_snapshot.operation_id != self.operation.operation_id
        ):
            raise ValueError("entry snapshot operation_id must match operation")
        if self.market_regime.feature_snapshot_id != self.entry_snapshot.snapshot_id:
            raise ValueError("market regime must be derived from entry snapshot")
        if self.entry_snapshot.as_of < self.operation.opened_at:
            raise ValueError("entry snapshot must not precede operation opened_at")
        if self.exit_snapshot is not None:
            if (
                self.exit_snapshot.operation_id is not None
                and self.exit_snapshot.operation_id != self.operation.operation_id
            ):
                raise ValueError("exit snapshot operation_id must match operation")
            if self.exit_snapshot.as_of < self.entry_snapshot.as_of:
                raise ValueError("exit snapshot must not precede entry snapshot")


class ExperienceEngine:
    """Assemble a validated experience aggregate from Phase 1/2 canonical objects."""

    def assemble(
        self,
        *,
        operation: Operation,
        entry_snapshot: FeatureSnapshot,
        market_regime: MarketRegime,
        outcome: Outcome,
        exit_snapshot: FeatureSnapshot | None = None,
    ) -> Experience:
        digest = sha256(
            (
                f"{operation.operation_id}|{entry_snapshot.snapshot_id}|"
                f"{market_regime.regime_id}|{outcome.outcome_id}"
            ).encode("utf-8")
        ).hexdigest()[:16]
        return Experience(
            experience_id=f"EXP-{digest}",
            operation=operation,
            entry_snapshot=entry_snapshot,
            market_regime=market_regime,
            outcome=outcome,
            exit_snapshot=exit_snapshot,
        )
