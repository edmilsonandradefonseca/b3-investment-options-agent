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