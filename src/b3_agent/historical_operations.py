from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from b3_agent.experience.operation_reconstruction import OperationMetadata, OperationReconstructor
from b3_agent.experience.outcome_engine import OutcomeEngine
from b3_agent.schemas.operation import Operation
from b3_agent.schemas.outcome import Outcome
from b3_agent.schemas.transaction import Transaction

@dataclass(frozen=True)
class HistoricalOperationsSnapshot:
    operations: tuple[Operation, ...]
    outcomes: tuple[Outcome, ...]
    open_operations: tuple[Operation, ...]
    closed_operations: tuple[Operation, ...]

class HistoricalOperationsService:
    """UC-07 reconstruction over the append-only execution ledger."""
    def build(self, transactions: Sequence[Transaction], *, metadata_by_ticker: Mapping[str, OperationMetadata] | None = None) -> HistoricalOperationsSnapshot:
        operations=OperationReconstructor().reconstruct(transactions, metadata_by_ticker=metadata_by_ticker)
        terminal={"CLOSED","ASSIGNED","EXERCISED","ROLLED"}
        closed=tuple(op for op in operations if op.status.value in terminal)
        opened=tuple(op for op in operations if op.status.value == "OPEN")
        outcomes=tuple(OutcomeEngine().finalize(op, transactions) for op in closed)
        return HistoricalOperationsSnapshot(operations,outcomes,opened,closed)
