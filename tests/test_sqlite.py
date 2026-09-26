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


def test_retrieval_trace_repository_round_trip(tmp_path):
    from datetime import datetime, timezone
    from b3_agent.repositories.retrieval_trace import RetrievalTraceRepository
    from b3_agent.schemas.experience import (
        ExperienceMatch,
        ExperienceRetrievalResult,
        RetrievalTrace,
        RetrievalTraceItem,
    )

    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()
    repository = RetrievalTraceRepository(store)

    trace = RetrievalTrace(
        trace_id="RTR-1",
        candidate_count=2,
        selected_count=1,
        retrieval_mode="structured+hybrid-fusion",
        fusion_method="RRF",
        ranker_version="experience-ranker-v2",
        items=(
            RetrievalTraceItem(
                reference_id="LRN-1",
                reference_type="LEARNING",
                fusion_score=0.8,
                initial_rank=2,
                final_rank=1,
                rerank_components=(
                    ("semantic_or_fusion", 0.8),
                    ("regime", 1.0),
                    ("temporal", 0.9),
                ),
            ),
        ),
    )
    retrieval = ExperienceRetrievalResult(
        query_id="EXPQ-1",
        as_of=datetime(2026, 9, 26, 15, 0, tzinfo=timezone.utc),
        subject_ids=("B3-PETR4",),
        matches=(
            ExperienceMatch(
                "LRN-1",
                "LEARNING",
                0.91,
                semantic_score=0.8,
                regime_score=1.0,
                temporal_score=0.9,
                fusion_score=0.8,
                initial_rank=2,
                final_rank=1,
            ),
        ),
        current_snapshot_id="FS-1",
        current_regime_id="REG-1",
        retrieval_metadata=(("ranker", "experience-ranker-v2"),),
        trace=trace,
    )

    repository.save(retrieval)
    saved = repository.get("RTR-1")

    assert saved is not None
    assert saved["query_id"] == "EXPQ-1"
    assert saved["fusion_method"] == "RRF"
    assert saved["subject_ids"] == ["B3-PETR4"]
    assert saved["trace_items"][0]["final_rank"] == 1
    assert repository.list_recent(limit=1)[0]["trace_id"] == "RTR-1"


def test_sqlite_schema_includes_retrieval_traces(tmp_path):
    store = SQLiteStore(tmp_path / "b3_agent.db")
    store.initialize()

    with store.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "retrieval_traces" in tables
