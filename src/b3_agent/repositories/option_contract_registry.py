from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class OptionContract:
    """Persistent metadata for an option contract, independent of current holdings."""

    option_ticker: str
    expiration_date: date | None = None
    option_type: str | None = None
    strike: float | None = None
    underlying_ticker: str | None = None
    contract_multiplier: float | None = None
    source_ref: str = ""


class OptionContractRegistry:
    """SQLite registry that keeps contract metadata after positions are closed."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS option_contracts (
                    option_ticker TEXT PRIMARY KEY,
                    expiration_date TEXT,
                    option_type TEXT,
                    strike REAL,
                    underlying_ticker TEXT,
                    contract_multiplier REAL,
                    source_ref TEXT NOT NULL DEFAULT ''
                )
                """
            )

    def upsert(self, contract: OptionContract) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO option_contracts (
                    option_ticker, expiration_date, option_type, strike,
                    underlying_ticker, contract_multiplier, source_ref
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(option_ticker) DO UPDATE SET
                    expiration_date = COALESCE(excluded.expiration_date, option_contracts.expiration_date),
                    option_type = COALESCE(excluded.option_type, option_contracts.option_type),
                    strike = COALESCE(excluded.strike, option_contracts.strike),
                    underlying_ticker = COALESCE(excluded.underlying_ticker, option_contracts.underlying_ticker),
                    contract_multiplier = COALESCE(excluded.contract_multiplier, option_contracts.contract_multiplier),
                    source_ref = CASE
                        WHEN excluded.source_ref <> '' THEN excluded.source_ref
                        ELSE option_contracts.source_ref
                    END
                """,
                (
                    contract.option_ticker,
                    contract.expiration_date.isoformat() if contract.expiration_date else None,
                    contract.option_type,
                    contract.strike,
                    contract.underlying_ticker,
                    contract.contract_multiplier,
                    contract.source_ref,
                ),
            )

    def upsert_many(self, contracts: list[OptionContract] | tuple[OptionContract, ...]) -> int:
        for contract in contracts:
            self.upsert(contract)
        return len(contracts)

    def get(self, option_ticker: str) -> OptionContract | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT option_ticker, expiration_date, option_type, strike,
                       underlying_ticker, contract_multiplier, source_ref
                FROM option_contracts
                WHERE option_ticker = ?
                """,
                (option_ticker,),
            ).fetchone()

        if row is None:
            return None

        return OptionContract(
            option_ticker=row[0],
            expiration_date=date.fromisoformat(row[1]) if row[1] else None,
            option_type=row[2],
            strike=row[3],
            underlying_ticker=row[4],
            contract_multiplier=row[5],
            source_ref=row[6],
        )

    def list_all(self) -> tuple[OptionContract, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT option_ticker, expiration_date, option_type, strike,
                       underlying_ticker, contract_multiplier, source_ref
                FROM option_contracts
                ORDER BY option_ticker
                """
            ).fetchall()

        return tuple(
            OptionContract(
                option_ticker=row[0],
                expiration_date=date.fromisoformat(row[1]) if row[1] else None,
                option_type=row[2],
                strike=row[3],
                underlying_ticker=row[4],
                contract_multiplier=row[5],
                source_ref=row[6],
            )
            for row in rows
        )
