from datetime import datetime, timezone

import pytest

from b3_agent.schemas.operation import Operation, OperationDirection, OperationStatus


def ts(day: int) -> datetime:
    return datetime(2026, 9, day, 15, 0, tzinfo=timezone.utc)


def test_open_operation_preserves_source_transactions_and_context_links():
    operation = Operation(
        operation_id="OP-PETR4-PUT-001",
        strategy_type="SHORT_PUT",
        underlying_id="B3-PETR4",
        opened_at=ts(1),
        status=OperationStatus.OPEN,
        direction=OperationDirection.SHORT,
        quantity=100,
        capital_committed=3500.0,
        instrument_ids=("B3-PETR4", "PETRV350"),
        option_leg_ids=("PETRV350",),
        source_transaction_ids=("TX-001",),
        broker_refs=("BTG",),
        entry_snapshot_id="FS-001",
        source_refs=("broker:btg:TX-001",),
        provenance="reconstructed_from_broker_transactions",
    )

    assert operation.operation_id == "OP-PETR4-PUT-001"
    assert operation.status == OperationStatus.OPEN
    assert operation.source_transaction_ids == ("TX-001",)
    assert operation.entry_snapshot_id == "FS-001"


def test_closed_operation_requires_timezone_aware_close_after_open():
    operation = Operation(
        operation_id="OP-PETR4-PUT-002",
        strategy_type="SHORT_PUT",
        underlying_id="B3-PETR4",
        opened_at=ts(1),
        closed_at=ts(10),
        status=OperationStatus.CLOSED,
        direction=OperationDirection.SHORT,
        source_transaction_ids=("TX-OPEN", "TX-CLOSE"),
        outcome_id="OUT-002",
    )

    assert operation.closed_at == ts(10)
    assert operation.outcome_id == "OUT-002"


def test_terminal_operation_requires_closed_at():
    with pytest.raises(ValueError, match="CLOSED operation requires closed_at"):
        Operation(
            operation_id="OP-003",
            strategy_type="SHORT_PUT",
            underlying_id="B3-PETR4",
            opened_at=ts(1),
            status=OperationStatus.CLOSED,
        )


def test_open_operation_rejects_closed_at():
    with pytest.raises(ValueError, match="OPEN operation must not have closed_at"):
        Operation(
            operation_id="OP-004",
            strategy_type="LONG_STOCK",
            underlying_id="B3-VALE3",
            opened_at=ts(1),
            closed_at=ts(2),
            status=OperationStatus.OPEN,
            direction=OperationDirection.LONG,
        )


def test_operation_rejects_naive_opened_at():
    with pytest.raises(ValueError, match="opened_at must be timezone-aware"):
        Operation(
            operation_id="OP-005",
            strategy_type="LONG_STOCK",
            underlying_id="B3-VALE3",
            opened_at=datetime(2026, 9, 1, 15, 0),
            status=OperationStatus.OPEN,
        )


def test_roll_operation_can_link_predecessor_and_successor():
    rolled = Operation(
        operation_id="OP-ROLL-002",
        strategy_type="SHORT_PUT",
        underlying_id="B3-PETR4",
        opened_at=ts(5),
        closed_at=ts(20),
        status=OperationStatus.ROLLED,
        direction=OperationDirection.SHORT,
        predecessor_operation_ids=("OP-ROLL-001",),
        successor_operation_ids=("OP-ROLL-003",),
    )

    assert rolled.predecessor_operation_ids == ("OP-ROLL-001",)
    assert rolled.successor_operation_ids == ("OP-ROLL-003",)


def test_operation_rejects_self_link():
    with pytest.raises(ValueError, match="own predecessor"):
        Operation(
            operation_id="OP-SELF",
            strategy_type="SHORT_PUT",
            underlying_id="B3-PETR4",
            opened_at=ts(1),
            status=OperationStatus.OPEN,
            predecessor_operation_ids=("OP-SELF",),
        )
