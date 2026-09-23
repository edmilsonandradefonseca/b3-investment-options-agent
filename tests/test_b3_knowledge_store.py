from datetime import datetime, timedelta, timezone

import pytest

from b3_agent.knowledge.models import KnowledgeRecord
from b3_agent.knowledge.sqlite_store import B3KnowledgeStore


def make_record(
    knowledge_id="TEST-001",
    version="1.0",
):
    now = datetime.now(timezone.utc)

    return KnowledgeRecord(
        knowledge_id=knowledge_id,
        topic="Test Discovery",
        category="test",
        status="DISCOVERED",
        version=version,
        created_at=now,
        updated_at=now,
        source="unit-test",
        evidence="Test evidence",
        content="Test content",
    )


def test_store_creates_database(tmp_path):
    db = tmp_path / "b3_knowledge.db"

    store = B3KnowledgeStore(db)

    assert db.exists()
    assert store.count() == 0


def test_record_discovery_and_get(tmp_path):
    store = B3KnowledgeStore(tmp_path / "b3_knowledge.db")
    record = make_record()

    result = store.record_discovery(record)

    assert result == ("TEST-001", "1.0")

    loaded = store.get("TEST-001", "1.0")

    assert loaded is not None
    assert loaded.knowledge_id == "TEST-001"
    assert loaded.version == "1.0"
    assert loaded.content == "Test content"


def test_get_latest_version(tmp_path):
    store = B3KnowledgeStore(tmp_path / "b3_knowledge.db")

    store.record_discovery(make_record(version="1.0"))
    store.record_discovery(make_record(version="2.0"))

    loaded = store.get("TEST-001")

    assert loaded is not None
    assert loaded.version == "2.0"


def test_versions_are_preserved(tmp_path):
    store = B3KnowledgeStore(tmp_path / "b3_knowledge.db")

    store.record_discovery(make_record(version="1.0"))
    store.record_discovery(make_record(version="2.0"))

    assert store.count() == 2


def test_duplicate_version_is_rejected(tmp_path):
    store = B3KnowledgeStore(tmp_path / "b3_knowledge.db")
    record = make_record()

    store.record_discovery(record)

    with pytest.raises(Exception):
        store.record_discovery(record)


def test_search(tmp_path):
    store = B3KnowledgeStore(tmp_path / "b3_knowledge.db")

    store.record_discovery(
        make_record(
            knowledge_id="ITUB4-001",
            version="1.0",
        )
    )

    results = store.search("Test Content")

    assert len(results) == 1
    assert results[0].knowledge_id == "ITUB4-001"


def test_archive_hides_record(tmp_path):
    store = B3KnowledgeStore(tmp_path / "b3_knowledge.db")

    store.record_discovery(make_record())

    store.archive("TEST-001", "1.0")

    assert store.get("TEST-001", "1.0") is None
    assert store.count() == 0


def test_retention_candidate(tmp_path):
    store = B3KnowledgeStore(tmp_path / "b3_knowledge.db")

    now = datetime.now(timezone.utc)

    record = KnowledgeRecord(
        knowledge_id="OLD-001",
        topic="Old",
        category="market",
        status="ACTIVE",
        version="1.0",
        created_at=now - timedelta(days=400),
        updated_at=now - timedelta(days=400),
        source="unit-test",
        evidence="old evidence",
        content="old content",
    )

    store.record_discovery(
        record,
        as_of=now - timedelta(days=400),
        retention_days=365,
    )

    candidates = store.retention_candidates()

    assert len(candidates) == 1
    assert candidates[0]["knowledge_id"] == "OLD-001"
