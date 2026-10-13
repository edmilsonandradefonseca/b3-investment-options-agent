from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from b3_agent.schemas.transaction import Transaction


class TransactionRepository:
    """Persistent append-only ledger for user-entered stock/option executions."""

    def __init__(self, database_path: str):
        self.database_path = database_path

    def add(self, transaction: Transaction) -> Transaction:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO transactions (
                    transaction_id, executed_at, action, instrument_type,
                    ticker, quantity, price, broker, source_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction.transaction_id,
                    transaction.executed_at.isoformat(),
                    transaction.action,
                    transaction.instrument_type,
                    transaction.ticker.upper().strip(),
                    transaction.quantity,
                    transaction.price,
                    transaction.broker.strip(),
                    transaction.source_ref,
                ),
            )
            connection.commit()
        return transaction

    def append_many(self, transactions: tuple[Transaction, ...]) -> int:
        """Append note-derived stock executions idempotently by transaction ID."""
        inserted = 0
        with sqlite3.connect(self.database_path) as connection:
            for transaction in transactions:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO transactions (
                        transaction_id, executed_at, action, instrument_type,
                        ticker, quantity, price, broker, source_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transaction.transaction_id,
                        transaction.executed_at.isoformat(),
                        transaction.action,
                        transaction.instrument_type,
                        transaction.ticker.upper().strip(),
                        transaction.quantity,
                        transaction.price,
                        transaction.broker.strip(),
                        transaction.source_ref,
                    ),
                )
                inserted += cursor.rowcount
            connection.commit()
        return inserted

    def list_by_source_prefix(self, prefix: str) -> tuple[Transaction, ...]:
        """Read transactions imported from one provenance namespace."""
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, executed_at, action, instrument_type,
                       ticker, quantity, price, broker, source_ref
                FROM transactions
                WHERE source_ref LIKE ?
                ORDER BY executed_at, transaction_id
                """,
                (f"{prefix}%",),
            ).fetchall()
        return tuple(
            Transaction(
                transaction_id=row[0],
                executed_at=datetime.fromisoformat(row[1]),
                action=row[2],
                instrument_type=row[3],
                ticker=row[4],
                quantity=row[5],
                price=row[6],
                broker=row[7] or "",
                source_ref=row[8] or "",
            )
            for row in rows
        )

    def list(self, limit: int = 100) -> tuple[Transaction, ...]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, executed_at, action, instrument_type,
                       ticker, quantity, price, broker, source_ref
                FROM transactions
                ORDER BY executed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return tuple(
            Transaction(
                transaction_id=row[0],
                executed_at=datetime.fromisoformat(row[1]),
                action=row[2],
                instrument_type=row[3],
                ticker=row[4],
                quantity=row[5],
                price=row[6],
                broker=row[7] or "",
                source_ref=row[8] or "",
            )
            for row in rows
        )
