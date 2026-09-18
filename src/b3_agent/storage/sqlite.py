import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    instrument_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    exchange TEXT NOT NULL,
    currency TEXT NOT NULL,
    underlying_id TEXT,
    sector TEXT,
    industry TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    active_from TEXT,
    active_to TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS data_sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    provider_type TEXT NOT NULL,
    base_url TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    records_read INTEGER NOT NULL DEFAULT 0,
    records_written INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    FOREIGN KEY (source_id) REFERENCES data_sources(source_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    executed_at TEXT NOT NULL,
    action TEXT NOT NULL,
    instrument_type TEXT NOT NULL,
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    broker TEXT,
    source_ref TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_executed_at
    ON transactions(executed_at);

CREATE INDEX IF NOT EXISTS idx_transactions_ticker
    ON transactions(ticker);

CREATE TABLE IF NOT EXISTS dataset_references (
    dataset_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL UNIQUE,
    storage_format TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    partition_strategy TEXT,
    first_observation TEXT,
    last_observation TEXT,
    created_at TEXT,
    updated_at TEXT
);
"""


class SQLiteStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with self.connect() as connection:
            connection.executescript(SCHEMA)
            connection.commit()
