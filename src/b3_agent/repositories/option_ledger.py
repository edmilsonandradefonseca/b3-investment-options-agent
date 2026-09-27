from __future__ import annotations

import hashlib
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

    @staticmethod
    def fingerprint(transaction: OptionTransaction) -> str:
        """Stable economic fingerprint used to make repeated ingestion idempotent."""
        values = (
            transaction.option_ticker.strip().upper(),
            transaction.broker.strip().upper(),
            transaction.quantity,
            transaction.average_cost,
            transaction.total_cost,
            transaction.as_of.isoformat() if transaction.as_of is not None else None,
            transaction.note_number,
        )
        payload = "|".join("" if value is None else str(value) for value in values)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

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
                    note_number TEXT,
                    source_type TEXT NOT NULL DEFAULT 'UNKNOWN',
                    source_id TEXT,
                    fingerprint TEXT
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(option_transactions)").fetchall()}
            if "fingerprint" not in columns:
                connection.execute("ALTER TABLE option_transactions ADD COLUMN fingerprint TEXT")
            if "source_type" not in columns:
                connection.execute("ALTER TABLE option_transactions ADD COLUMN source_type TEXT NOT NULL DEFAULT 'UNKNOWN'")
            if "source_id" not in columns:
                connection.execute("ALTER TABLE option_transactions ADD COLUMN source_id TEXT")
            connection.execute("UPDATE option_transactions SET fingerprint = transaction_id WHERE fingerprint IS NULL")
            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_option_transactions_fingerprint
                ON option_transactions(fingerprint)
                """)
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
                        average_cost, total_cost, as_of, source_ref, note_number,
                        source_type, source_id, fingerprint
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        transaction.source_type,
                        transaction.source_id,
                        self.fingerprint(transaction),
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
                       average_cost, total_cost, as_of, source_ref, note_number,
                       source_type, source_id
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
                source_type=row[9] or "UNKNOWN",
                source_id=row[10],
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
