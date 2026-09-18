from datetime import datetime, timezone

from b3_agent.repositories.transaction import TransactionRepository
from b3_agent.schemas.transaction import Transaction
from b3_agent.storage.sqlite import SQLiteStore


def test_transaction_is_persistent_and_ordered(tmp_path):
    database = tmp_path / "b3.db"
    store = SQLiteStore(database)
    store.initialize()

    repository = TransactionRepository(str(database))
    first = Transaction(
        transaction_id="tx-1",
        executed_at=datetime(2026, 9, 17, 10, tzinfo=timezone.utc),
        action="BUY",
        instrument_type="STOCK",
        ticker="petr4",
        quantity=100,
        price=32.5,
    )
    second = Transaction(
        transaction_id="tx-2",
        executed_at=datetime(2026, 9, 17, 11, tzinfo=timezone.utc),
        action="SELL",
        instrument_type="STOCK",
        ticker="PETR4",
        quantity=20,
        price=34,
    )

    repository.add(first)
    repository.add(second)
    result = repository.list()

    assert [item.transaction_id for item in result] == ["tx-2", "tx-1"]
    assert result[1].signed_quantity == 100
    assert result[0].signed_quantity == -20


def test_transaction_contract_rejects_invalid_values():
    from pytest import raises

    with raises(ValueError):
        Transaction(
            transaction_id="x",
            executed_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
            action="HOLD",
            instrument_type="STOCK",
            ticker="PETR4",
            quantity=1,
            price=1,
        )
