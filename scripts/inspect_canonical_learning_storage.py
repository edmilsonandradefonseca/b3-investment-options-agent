#!/usr/bin/env python3
"""Read schemas of the three known runtime SQLite owners; no rows or discovery."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from time import monotonic

DATABASES = ("b3_agent.db", "options.sqlite3", "source_manifest.sqlite3")


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
    args = parser.parse_args()
    print(json.dumps(inspect(args.data_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
