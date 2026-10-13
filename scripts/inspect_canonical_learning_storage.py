#!/usr/bin/env python3
"""Read schemas of the three known runtime SQLite owners; no rows or discovery."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from time import monotonic

DATABASES = ("b3_agent.db", "options.sqlite3", "source_manifest.sqlite3")


def inspect_registered_datasets(data_dir):
    """Inspect metadata for declared files only; never discover directory contents."""
    root = Path(data_dir).resolve()
    database = root / "b3_agent.db"
    result = {"scope": "REGISTERED_DATASET_SCHEMAS_ONLY", "business_rows_read": False,
              "canonical_ownership": "REQUIRES_SCHEMA_AND_ADAPTER_REVIEW", "datasets": []}
    if not database.is_file():
        return {**result, "status": "MISSING_DATABASE"}
    try:
        with closing(sqlite3.connect(database.as_uri()+"?mode=ro", uri=True, timeout=2)) as connection:
            connection.execute("PRAGMA query_only=ON")
            deadline = monotonic() + 3
            connection.set_progress_handler(lambda: int(monotonic() > deadline), 1000)
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT dataset_id, dataset_name, storage_format, storage_path, schema_version, partition_strategy FROM dataset_references ORDER BY dataset_id LIMIT 101").fetchall()
        result.update(status="READ_OK", registry_truncated=len(rows)>100)
        for row in rows[:100]:
            item = dict(row)
            item["columns"] = []
            raw = row["storage_path"]
            if not isinstance(raw, str) or not raw.strip():
                item["schema_status"] = "INVALID_PATH"
            else:
                try:
                    declared = Path(raw)
                    target = (declared if declared.is_absolute() else root / declared).resolve()
                    if not target.is_relative_to(root):
                        item["schema_status"] = "OUTSIDE_DATA_DIRECTORY"
                    elif not target.exists():
                        item["schema_status"] = "MISSING_PATH"
                    elif target.is_dir():
                        item["schema_status"] = "DIRECTORY_NOT_SCANNED"
                    elif str(row["storage_format"]).casefold() != "parquet":
                        item["schema_status"] = "FORMAT_NOT_INSPECTED"
                    else:
                        import pyarrow.parquet as pq
                        with target.open("rb") as source:
                            schema = pq.ParquetFile(source).schema_arrow
                        item["columns"] = [{"column": field.name, "type": str(field.type)} for field in schema]
                        item["schema_status"] = "FILE_SCHEMA_READ_OK"
                except (OSError, ValueError, RuntimeError) as error:
                    item.update(schema_status="UNAVAILABLE_SCHEMA", error_type=type(error).__name__)
            result["datasets"].append(item)
    except (OSError, sqlite3.Error) as error:
        result.update(status="UNAVAILABLE_REGISTRY", error_type=type(error).__name__)
    return result


def inspect(data_dir):
    result = {}
    for name in DATABASES:
        path = Path(data_dir) / name
        if not path.is_file():
            result[name] = {"status": "MISSING", "tables": {}}
            continue
        try:
            with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True, timeout=2)) as connection:
                connection.execute("PRAGMA query_only=ON")
                deadline = monotonic() + 3
                connection.set_progress_handler(lambda: int(monotonic() > deadline), 1000)
                connection.execute("BEGIN")
                names = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name LIMIT 101").fetchall()
                tables = {}
                for (table,) in names[:100]:
                    quoted = table.replace('"', '""')
                    tables[table] = [{"column": row[1], "type": row[2], "primary_key": bool(row[5])}
                                     for row in connection.execute(f'PRAGMA table_info("{quoted}")')]
                result[name] = {"status": "READ_OK", "tables": tables, "tables_truncated": len(names)>100}
        except (OSError, sqlite3.Error) as error:
            result[name] = {"status": "UNAVAILABLE", "error_type": type(error).__name__, "tables": {}}
    return {"scope": "KNOWN_RUNTIME_SQLITE_SCHEMAS_ONLY", "row_data_read": False,
            "canonical_ownership": "REQUIRES_SCHEMA_AND_ADAPTER_REVIEW", "databases": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--registered-datasets", action="store_true", help="Read dataset registry and declared Parquet file schemas only; skip the completed SQLite schema inventory")
    args = parser.parse_args()
    read = inspect_registered_datasets if args.registered_datasets else inspect
    print(json.dumps(read(args.data_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
