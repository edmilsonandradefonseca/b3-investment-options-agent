from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class PortfolioSnapshot:
    as_of: date
    total_value: float
    stocks_value: float
    options_value: float
    cash: float
    pnl: float


class PortfolioSnapshotRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    as_of TEXT PRIMARY KEY,
                    total_value REAL NOT NULL,
                    stocks_value REAL NOT NULL,
                    options_value REAL NOT NULL,
                    cash REAL NOT NULL,
                    pnl REAL NOT NULL
                )
                """
            )
            conn.commit()

    def upsert(self, snapshot: PortfolioSnapshot) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO portfolio_snapshots
                (as_of, total_value, stocks_value, options_value, cash, pnl)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(as_of) DO UPDATE SET
                    total_value=excluded.total_value,
                    stocks_value=excluded.stocks_value,
                    options_value=excluded.options_value,
                    cash=excluded.cash,
                    pnl=excluded.pnl
                """,
                (
                    snapshot.as_of.isoformat(),
                    snapshot.total_value,
                    snapshot.stocks_value,
                    snapshot.options_value,
                    snapshot.cash,
                    snapshot.pnl,
                ),
            )
            conn.commit()

    def list_all(self) -> tuple[PortfolioSnapshot, ...]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT as_of, total_value, stocks_value, options_value, cash, pnl
                FROM portfolio_snapshots
                ORDER BY as_of
                """
            ).fetchall()
        return tuple(
            PortfolioSnapshot(
                as_of=date.fromisoformat(r[0]),
                total_value=r[1],
                stocks_value=r[2],
                options_value=r[3],
                cash=r[4],
                pnl=r[5],
            )
            for r in rows
        )
