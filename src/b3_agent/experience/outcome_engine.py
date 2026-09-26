from __future__ import annotations

from collections.abc import Iterable

from b3_agent.experience.events import OutcomeFinalized
from b3_agent.schemas.operation import Operation, OperationStatus
from b3_agent.schemas.outcome import Outcome, OutcomeStatus
from b3_agent.schemas.transaction import Transaction


class OutcomeEngine:
    """Deterministically finalize realized outcomes from operation ledger rows."""

    TERMINAL = {
        OperationStatus.CLOSED,
        OperationStatus.ASSIGNED,
        OperationStatus.EXERCISED,
        OperationStatus.ROLLED,
    }

    def finalize(
        self,
        operation: Operation,
        transactions: Iterable[Transaction],
    ) -> Outcome:
        if operation.status not in self.TERMINAL:
            raise ValueError("operation must be terminal before outcome finalization")
        if operation.closed_at is None:
            raise ValueError("terminal operation requires closed_at")

        by_id = {transaction.transaction_id: transaction for transaction in transactions}
        missing = [
            transaction_id
            for transaction_id in operation.source_transaction_ids
            if transaction_id not in by_id
        ]
        if missing:
            raise ValueError(f"missing source transactions: {missing}")

        rows = [by_id[transaction_id] for transaction_id in operation.source_transaction_ids]
        realized_pnl = sum(
            (
                transaction.quantity * transaction.price
                if transaction.action == "SELL"
                else -transaction.quantity * transaction.price
            )
            for transaction in rows
        )

        realized_return = None
        if operation.capital_committed is not None and operation.capital_committed > 0:
            realized_return = realized_pnl / operation.capital_committed

        holding_period_days = max(
            0,
            (operation.closed_at.date() - operation.opened_at.date()).days,
        )

        return Outcome(
            outcome_id=f"OUT-{operation.operation_id}",
            operation_id=operation.operation_id,
            finalized_at=operation.closed_at,
            status=OutcomeStatus.FINAL,
            realized_pnl=realized_pnl,
            realized_return=realized_return,
            holding_period_days=holding_period_days,
            assigned=operation.status == OperationStatus.ASSIGNED,
            exercised=operation.status == OperationStatus.EXERCISED,
            source_refs=tuple(
                dict.fromkeys(transaction.source_ref for transaction in rows)
            ),
            provenance="outcome_engine:v1",
            schema_version="1.0",
        )

    def finalize_with_event(
        self,
        operation: Operation,
        transactions: Iterable[Transaction],
    ) -> tuple[Outcome, OutcomeFinalized]:
        outcome = self.finalize(operation, transactions)
        return outcome, OutcomeFinalized.from_outcome(outcome)
