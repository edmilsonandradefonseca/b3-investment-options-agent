from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from collections import defaultdict
from collections.abc import Iterable, Mapping

from b3_agent.schemas.operation import (
    Operation,
    OperationDirection,
    OperationStatus,
)
from b3_agent.schemas.transaction import Transaction


class OperationReconstructionError(ValueError):
    """Raised when an economic operation cannot be reconstructed deterministically."""


@dataclass(frozen=True)
class OperationMetadata:
    underlying_id: str
    strategy_type: str
    instrument_ids: tuple[str, ...] = ()
    option_leg_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.underlying_id.strip():
            raise ValueError("underlying_id must be non-empty")
        if not self.strategy_type.strip():
            raise ValueError("strategy_type must be non-empty")


class OperationReconstructor:
    """Reconstruct economic operations from the append-only execution ledger.

    V1 intentionally rejects a single execution that flips an existing position
    through zero because the canonical Transaction contract does not carry split
    quantities. Such records must be normalized/split upstream before learning.
    """

    def reconstruct(
        self,
        transactions: Iterable[Transaction],
        *,
        metadata_by_ticker: Mapping[str, OperationMetadata] | None = None,
    ) -> tuple[Operation, ...]:
        metadata_by_ticker = {
            key.upper().strip(): value
            for key, value in (metadata_by_ticker or {}).items()
        }

        grouped: dict[str, list[Transaction]] = defaultdict(list)
        for transaction in transactions:
            grouped[transaction.ticker.upper().strip()].append(transaction)

        operations: list[Operation] = []
        for ticker in sorted(grouped):
            ordered = sorted(
                grouped[ticker],
                key=lambda item: (item.executed_at, item.transaction_id),
            )
            operations.extend(
                self._reconstruct_ticker(
                    ticker,
                    ordered,
                    metadata_by_ticker.get(ticker),
                )
            )

        return tuple(
            sorted(
                operations,
                key=lambda item: (item.opened_at, item.operation_id),
            )
        )

    def _reconstruct_ticker(
        self,
        ticker: str,
        transactions: list[Transaction],
        metadata: OperationMetadata | None,
    ) -> list[Operation]:
        output: list[Operation] = []
        current_ids: list[str] = []
        current_refs: list[str] = []
        opened_at = None
        opening_direction: OperationDirection | None = None
        opening_quantity: float | None = None
        running_quantity = 0.0
        instrument_type: str | None = None

        def finalize(closed_at=None) -> None:
            nonlocal current_ids, current_refs, opened_at
            nonlocal opening_direction, opening_quantity, running_quantity, instrument_type

            if not current_ids or opened_at is None or opening_direction is None:
                return

            status = (
                OperationStatus.CLOSED
                if abs(running_quantity) < 1e-12
                else OperationStatus.OPEN
            )
            effective_closed_at = closed_at if status == OperationStatus.CLOSED else None

            resolved = metadata or _default_metadata(
                ticker=ticker,
                instrument_type=instrument_type or "STOCK",
                direction=opening_direction,
            )
            digest = sha256(
                "|".join([ticker, *current_ids]).encode("utf-8")
            ).hexdigest()[:16]

            output.append(
                Operation(
                    operation_id=f"OP-{ticker}-{digest}",
                    strategy_type=resolved.strategy_type,
                    underlying_id=resolved.underlying_id,
                    opened_at=opened_at,
                    closed_at=effective_closed_at,
                    status=status,
                    direction=opening_direction,
                    quantity=opening_quantity,
                    instrument_ids=(
                        resolved.instrument_ids
                        if resolved.instrument_ids
                        else (f"B3-{ticker}",)
                    ),
                    option_leg_ids=resolved.option_leg_ids,
                    source_transaction_ids=tuple(current_ids),
                    broker_refs=tuple(
                        sorted(
                            {
                                transaction.broker.strip()
                                for transaction in transactions
                                if transaction.transaction_id in current_ids
                                and transaction.broker.strip()
                            }
                        )
                    ),
                    source_refs=tuple(current_refs),
                    provenance="operation_reconstruction:v1",
                    schema_version="1.0",
                )
            )

            current_ids = []
            current_refs = []
            opened_at = None
            opening_direction = None
            opening_quantity = None
            running_quantity = 0.0
            instrument_type = None

        for transaction in transactions:
            delta = transaction.signed_quantity
            if abs(running_quantity) < 1e-12:
                opened_at = transaction.executed_at
                opening_direction = (
                    OperationDirection.LONG
                    if delta > 0
                    else OperationDirection.SHORT
                )
                opening_quantity = abs(delta)
                instrument_type = transaction.instrument_type
            elif transaction.instrument_type != instrument_type:
                raise OperationReconstructionError(
                    f"mixed instrument_type for ticker {ticker}"
                )

            next_quantity = running_quantity + delta

            if (
                abs(running_quantity) > 1e-12
                and abs(next_quantity) > 1e-12
                and (running_quantity > 0) != (next_quantity > 0)
            ):
                raise OperationReconstructionError(
                    f"transaction {transaction.transaction_id} crosses position through zero; "
                    "split it upstream before operation reconstruction"
                )

            current_ids.append(transaction.transaction_id)
            current_refs.append(transaction.source_ref)
            running_quantity = next_quantity

            if abs(running_quantity) < 1e-12:
                finalize(closed_at=transaction.executed_at)

        finalize()
        return output


def _default_metadata(
    *,
    ticker: str,
    instrument_type: str,
    direction: OperationDirection,
) -> OperationMetadata:
    if instrument_type == "STOCK":
        strategy = "LONG_STOCK" if direction == OperationDirection.LONG else "SHORT_STOCK"
    else:
        strategy = "LONG_OPTION" if direction == OperationDirection.LONG else "SHORT_OPTION"

    return OperationMetadata(
        underlying_id=f"B3-{ticker}",
        strategy_type=strategy,
        instrument_ids=(f"B3-{ticker}",),
        option_leg_ids=(ticker,) if instrument_type == "OPTION" else (),
    )
