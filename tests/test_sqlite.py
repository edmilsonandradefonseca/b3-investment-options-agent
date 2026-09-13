import sqlite3

from b3_agent.storage.sqlite import SQLiteStore


def test_sqlite_store_initializes_schema(tmp_path):
    database_path = tmp_path / "b3_agent.db"
    store = SQLiteStore(database_path)

    store.initialize()

    assert database_path.exists()

    with store.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }

    assert {
        "instruments",
        "data_sources",
        "ingestion_runs",
        "dataset_references",
    }.issubset(tables)


def test_sqlite_store_enables_foreign_keys(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()

    with store.connect() as connection:
        foreign_keys = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

    assert foreign_keys == 1


def test_sqlite_store_initialization_is_idempotent(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")

    store.initialize()
    store.initialize()

    with store.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table'"
        ).fetchone()[0]

    assert count >= 4
