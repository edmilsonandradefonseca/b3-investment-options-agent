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


def registry(tmp_path, records):
    with sqlite3.connect(tmp_path / "b3_agent.db") as connection:
        connection.execute("CREATE TABLE dataset_references (dataset_id TEXT, dataset_name TEXT, storage_format TEXT, storage_path TEXT, schema_version TEXT, partition_strategy TEXT)")
        connection.executemany("INSERT INTO dataset_references VALUES (?,?,?,?,?,?)", records)
    return runpy.run_path(str(Path(__file__).parents[1] / "scripts/inspect_canonical_learning_storage.py"))["inspect_registered_datasets"]


def test_registered_files_are_schema_only_without_directory_scans(tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    target = tmp_path / "declared.parquet"
    pq.write_table(pa.table({"outcome_id": ["private-outcome-value"], "realized_pnl": [123456.789]}), target)
    folder = tmp_path / "registered-folder"
    folder.mkdir()
    inspect = registry(tmp_path, [
        ("1", "outcomes", "Parquet", "declared.parquet", "1.0", None),
        ("2", "partitioned", "Parquet", "registered-folder", "1.0", "ticker"),
        ("3", "missing", "Parquet", "missing.parquet", "1.0", None),
        ("4", "external", "Parquet", str(tmp_path.parent / "external.parquet"), "1.0", None),
    ])
    before = target.read_bytes(), (tmp_path / "b3_agent.db").read_bytes()
    monkeypatch.setattr(pq, "read_table", lambda *a, **k: (_ for _ in ()).throw(AssertionError("business table read")))
    monkeypatch.setattr(Path, "iterdir", lambda *a: (_ for _ in ()).throw(AssertionError("directory scanned")))
    result = inspect(tmp_path)
    assert result["business_rows_read"] is False
    assert [item["schema_status"] for item in result["datasets"]] == ["FILE_SCHEMA_READ_OK", "DIRECTORY_NOT_SCANNED", "MISSING_PATH", "OUTSIDE_DATA_DIRECTORY"]
    assert [item["column"] for item in result["datasets"][0]["columns"]] == ["outcome_id", "realized_pnl"]
    assert "private-outcome-value" not in str(result) and "123456.789" not in str(result)
    assert (target.read_bytes(), (tmp_path / "b3_agent.db").read_bytes()) == before
    assert not (tmp_path / "missing.parquet").exists()


def test_registry_is_bounded_and_missing_database_not_created(tmp_path):
    inspect = registry(tmp_path, [(str(i), "dataset", "Parquet", "missing.parquet", "1.0", None) for i in range(101)])
    result = inspect(tmp_path)
    assert result["registry_truncated"] is True
    assert len(result["datasets"]) == 100
    missing = tmp_path / "missing"
    assert inspect(missing)["status"] == "MISSING_DATABASE"
    assert not missing.exists()


def test_empty_registry_does_not_mean_no_unregistered_canonical_storage(tmp_path):
    result = registry(tmp_path, [])(tmp_path)
    assert result["status"] == "READ_OK"
    assert result["datasets"] == []
    assert result["canonical_ownership"] == "REQUIRES_SCHEMA_AND_ADAPTER_REVIEW"
