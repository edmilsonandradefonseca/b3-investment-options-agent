from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from b3_agent.schemas.option_transaction import OptionTransaction


class OptionTransactionLedger:
    """Append-only SQLite ledger for historical option transactions."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS option_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    option_ticker TEXT NOT NULL,
                    broker TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    average_cost REAL,
                    total_cost REAL,
                    as_of TEXT,
                    source_ref TEXT NOT NULL DEFAULT '',
                    note_number TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_option_transactions_ticker
                ON option_transactions(option_ticker)
                """
            )
            connection.commit()

    @staticmethod
    def _as_text(value: date | datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _as_date(value: str | None) -> date | datetime | None:
        if not value:
            return None
        return date.fromisoformat(value)

    def append(self, transactions: Iterable[OptionTransaction]) -> int:
        inserted = 0
        with self._connect() as connection:
            for transaction in transactions:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO option_transactions (
                        transaction_id, option_ticker, broker, quantity,
                        average_cost, total_cost, as_of, source_ref, note_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transaction.transaction_id,
                        transaction.option_ticker,
                        transaction.broker,
                        transaction.quantity,
                        transaction.average_cost,
                        transaction.total_cost,
                        self._as_text(transaction.as_of),
                        transaction.source_ref,
                        transaction.note_number,
                    ),
                )
                inserted += cursor.rowcount
            connection.commit()
        return inserted

    def list_all(self) -> tuple[OptionTransaction, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, option_ticker, broker, quantity,
                       average_cost, total_cost, as_of, source_ref, note_number
                FROM option_transactions
                ORDER BY as_of, transaction_id
                """
            ).fetchall()

        return tuple(
            OptionTransaction(
                transaction_id=row[0],
                option_ticker=row[1],
                broker=row[2],
                quantity=row[3],
                average_cost=row[4],
                total_cost=row[5],
                as_of=self._as_date(row[6]),
                source_ref=row[7],
                note_number=row[8],
            )
            for row in rows
        )

    def list_by_ticker(self, option_ticker: str) -> tuple[OptionTransaction, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT transaction_id, option_ticker, broker, quantity,
                       average_cost, total_cost, as_of, source_ref, note_number
                FROM option_transactions
                WHERE option_ticker = ?
                ORDER BY as_of, transaction_id
                """,
                (option_ticker,),
            ).fetchall()

        return tuple(
            OptionTransaction(
                transaction_id=row[0],
                option_ticker=row[1],
                broker=row[2],
                quantity=row[3],
                average_cost=row[4],
                total_cost=row[5],
                as_of=self._as_date(row[6]),
                source_ref=row[7],
                note_number=row[8],
            )
            for row in rows
        )
