from pathlib import Path
import runpy
import sqlite3


def inspector():
    return runpy.run_path(str(Path(__file__).parents[1] / "scripts/inspect_canonical_learning_storage.py"))["inspect"]


def test_known_schema_inspection_reads_no_rows_and_changes_no_bytes(tmp_path):
    target = tmp_path / "b3_agent.db"
    with sqlite3.connect(target) as connection:
        connection.execute('CREATE TABLE "odd""name" (id TEXT PRIMARY KEY, private_note TEXT)')
        connection.execute('INSERT INTO "odd""name" VALUES (?,?)', ("private-id", "private-note"))
    # A different, unlisted DB must not be inspected.
    other = tmp_path / "unknown.sqlite3"
    other.write_bytes(b"not sqlite")
    before = target.read_bytes()
    result = inspector()(tmp_path)
    assert result["row_data_read"] is False
    assert set(result["databases"]) == {"b3_agent.db", "options.sqlite3", "source_manifest.sqlite3"}
    assert result["databases"]["b3_agent.db"]["tables"]['odd"name'][0]["column"] == "id"
    assert "private-note" not in str(result) and "private-id" not in str(result)
    assert target.read_bytes() == before
    assert not (tmp_path / "options.sqlite3").exists()


def test_missing_directory_is_not_created(tmp_path):
    missing = tmp_path / "missing"
    result = inspector()(missing)
    assert all(item["status"] == "MISSING" for item in result["databases"].values())
    assert not missing.exists()
