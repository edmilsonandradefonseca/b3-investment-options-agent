from pathlib import Path

import pytest

from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore


def test_list_notes(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    (vault / "note.md").write_text("# Test", encoding="utf-8")
    (vault / "other.txt").write_text("ignore", encoding="utf-8")

    store = ObsidianKnowledgeStore(vault)

    assert store.list_notes() == [Path("note.md")]


def test_read_note(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    (vault / "note.md").write_text(
        "# B3\n\nBRAPI market data",
        encoding="utf-8",
    )

    store = ObsidianKnowledgeStore(vault)

    assert store.read_note("note.md") == "# B3\n\nBRAPI market data"


def test_write_note(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    store = ObsidianKnowledgeStore(vault)

    store.write_note(
        "04_Stocks/PETR4.md",
        "# PETR4\n\nInvestment thesis",
    )

    assert store.read_note("04_Stocks/PETR4.md") == (
        "# PETR4\n\nInvestment thesis"
    )


def test_search_is_case_insensitive(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    (vault / "note.md").write_text(
        "# BRAPI\n\nMarket data provider",
        encoding="utf-8",
    )

    store = ObsidianKnowledgeStore(vault)

    assert store.search("brapi") == [Path("note.md")]


def test_search_rejects_empty_query(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    store = ObsidianKnowledgeStore(vault)

    with pytest.raises(ValueError):
        store.search("   ")


def test_path_cannot_escape_vault(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    store = ObsidianKnowledgeStore(vault)

    with pytest.raises(ValueError):
        store.read_note("../outside.md")


def test_missing_vault_raises(tmp_path: Path):
    store = ObsidianKnowledgeStore(tmp_path / "does-not-exist")

    with pytest.raises(FileNotFoundError):
        store.list_notes()
from datetime import datetime, timezone

from b3_agent.knowledge.models import KnowledgeRecord


def test_record_discovery_creates_versioned_note(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    store = ObsidianKnowledgeStore(vault)

    now = datetime.now(timezone.utc)

    record = KnowledgeRecord(
        knowledge_id="TEST-001",
        topic="Test Discovery",
        category="test",
        status="DISCOVERED",
        version="1.0",
        created_at=now,
        updated_at=now,
        source="unit-test",
        evidence="Test evidence",
        content="Test content",
    )

    path = store.record_discovery(record)

    assert path == Path(
        "00_System/Knowledge/TEST-001/v1.0.md"
    )

    content = store.read_note(path)

    assert "# Test Discovery" in content
    assert "- Knowledge ID: TEST-001" in content
    assert "- Status: DISCOVERED" in content
    assert "- Version: 1.0" in content
    assert "- Source: unit-test" in content
    assert "Test evidence" in content
    assert "Test content" in content
