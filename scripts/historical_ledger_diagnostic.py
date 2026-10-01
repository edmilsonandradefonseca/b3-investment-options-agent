#!/usr/bin/env python3
"""Read-only runtime inventory. Never construct repositories or initialize stores."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import time

RUNTIME_ENV_FILES = (Path("/etc/b3-runtime.env"), Path("/opt/b3-runtime/b3.env"))
DEFAULT_RUNTIME_DATA = Path("/opt/b3-runtime/data")
# Never print arbitrary table payloads, credentials or source-document text.
SAFE_COLUMNS = frozenset("""
transaction_id option_ticker ticker broker quantity average_cost total_cost as_of
note_number source_type source_id executed_at action instrument_type price
imported_at record_count coverage_start coverage_end scope completeness
underlying underlying_id option_type strike expiry expiration available_at
""".split())
DATE_COLUMNS = ("as_of", "executed_at", "imported_at", "coverage_start", "coverage_end", "available_at")


def _env_file_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[7:]
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            if key.strip() == "B3_AGENT_DATA_DIR":
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _canonical_data_dir() -> Path:
    configured = os.getenv("B3_AGENT_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    merged = {}
    for path in RUNTIME_ENV_FILES:
        merged.update(_env_file_values(path))
    configured = merged.get("B3_AGENT_DATA_DIR")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_RUNTIME_DATA.resolve()


def _candidate_data_dirs(canonical_data_dir: Path | None = None) -> tuple[Path, ...]:
    values = (
        canonical_data_dir or _canonical_data_dir(),
        Path(__file__).resolve().parent.parent / "data",
        DEFAULT_RUNTIME_DATA,
        Path("/opt/b3-investment-options-agent/data"),
        Path.home() / "b3-investment-options-agent/data",
    )
    return tuple(dict.fromkeys(path.expanduser().resolve() for path in values))


def _identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _groups(conn, table, column):
    sql = f'SELECT {_identifier(column)}, COUNT(*) FROM {_identifier(table)} GROUP BY 1 ORDER BY 2 DESC LIMIT 40'
    return [{"value": row[0], "count": row[1]} for row in conn.execute(sql)]


def inspect_database(path: Path, *, sample_limit: int = 3, timeout_seconds: float = 15) -> dict:
    """Consistent per-file snapshot, including WAL. No immutable=1 shortcut."""
    result = {"path": str(path), "exists": path.is_file(), "tables": {}}
    if not result["exists"]:
        result["status"] = "MISSING"
        return result
    started = time.monotonic()
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)) as conn:
            conn.execute("PRAGMA query_only=ON")
            conn.set_progress_handler(lambda: int(time.monotonic() - started > timeout_seconds), 1000)
            conn.execute("BEGIN")
            names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            for name in names:
                quoted = _identifier(name)
                schema = list(conn.execute(f"PRAGMA table_info({quoted})"))
                columns = {row[1] for row in schema}
                entry = {
                    "schema": [{"name": row[1], "type": row[2], "not_null": bool(row[3]), "primary_key": row[5]} for row in schema],
                    "row_count": conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0],
                    "date_coverage": {},
                }
                result["tables"][name] = entry
                for column in DATE_COLUMNS:
                    if column in columns:
                        col = _identifier(column)
                        lo, hi, missing = conn.execute(f"SELECT MIN({col}), MAX({col}), COUNT(*)-COUNT({col}) FROM {quoted}").fetchone()
                        entry["date_coverage"][column] = {"min": lo, "max": hi, "null_count": missing}
                if name not in {"option_transactions", "transactions", "source_manifest"}:
                    continue
                for column in ("source_type", "completeness", "scope", "action", "instrument_type"):
                    if column in columns:
                        entry[column + "_counts"] = _groups(conn, name, column)
                selected = sorted(columns & SAFE_COLUMNS)
                if selected and sample_limit:
                    order_col = next((c for c in ("as_of", "executed_at", "imported_at") if c in columns), selected[0])
                    select = ",".join(_identifier(c) for c in selected)
                    rows = conn.execute(f"SELECT {select} FROM {quoted} ORDER BY {_identifier(order_col)} DESC LIMIT ?", (sample_limit,))
                    entry["representative_rows"] = [dict(zip(selected, row)) for row in rows]
                ticker = next((c for c in ("option_ticker", "ticker") if c in columns), None)
                if ticker:
                    col = _identifier(ticker)
                    entry["petr4_exact_rows"] = conn.execute(f"SELECT COUNT(*) FROM {quoted} WHERE UPPER({col})='PETR4'").fetchone()[0]
                    entry["petr_prefix_rows_underlying_unverified"] = conn.execute(f"SELECT COUNT(*) FROM {quoted} WHERE UPPER({col}) LIKE 'PETR%'").fetchone()[0]
                    entry["symbol_counts"] = _groups(conn, name, ticker)
                    if name == "option_transactions":
                        # This is a diagnostic hint only. Not canonical type/expiry metadata.
                        hint = f"CASE WHEN length({col})>=6 AND UPPER(substr({col},5,1)) BETWEEN 'A' AND 'L' THEN 'CALL_LETTER_HINT' WHEN length({col})>=6 AND UPPER(substr({col},5,1)) BETWEEN 'M' AND 'X' THEN 'PUT_LETTER_HINT' ELSE 'UNKNOWN' END"
                        entry["symbol_type_hints_not_contract_metadata"] = dict(conn.execute(f"SELECT {hint}, COUNT(*) FROM {quoted} GROUP BY 1"))
                if "quantity" in columns:
                    entry["quantity_sign_counts"] = dict(conn.execute(f"SELECT CASE WHEN quantity>0 THEN 'POSITIVE' WHEN quantity<0 THEN 'NEGATIVE' WHEN quantity=0 THEN 'ZERO' ELSE 'UNKNOWN' END, COUNT(*) FROM {quoted} GROUP BY 1"))
                if name == "option_transactions" and {"as_of", "average_cost", "quantity"} <= columns:
                    entry["canonical_uc07_usable_rows"] = conn.execute(f"SELECT COUNT(*) FROM {quoted} WHERE as_of IS NOT NULL AND average_cost IS NOT NULL AND average_cost>=0 AND quantity!=0").fetchone()[0]
                    entry["usable_definition"] = "candidate rows only; date parsing, metadata, source completeness, broker identity and PIT still require validation"
                    if "total_cost" in columns:
                        entry["amount_sign_mismatch_rows"] = conn.execute(f"SELECT COUNT(*) FROM {quoted} WHERE quantity * total_cost < 0").fetchone()[0]
                        entry["amount_price_mismatch_rows"] = conn.execute(f"SELECT COUNT(*) FROM {quoted} WHERE ABS(total_cost-quantity*average_cost)>0.011").fetchone()[0]
            conn.rollback()
        result["status"] = "READ_OK"
    except (sqlite3.Error, OSError) as exc:
        result["status"] = "READ_ERROR"
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["latency_ms"] = round((time.monotonic() - started) * 1000, 3)
    return result


def build_report(canonical_data_dir: Path, *, sample_limit: int = 3) -> dict:
    canonical = canonical_data_dir / "options.sqlite3"
    canonical_manifest = canonical_data_dir / "source_manifest.sqlite3"
    directories = _candidate_data_dirs(canonical_data_dir)
    paths = {canonical, canonical_manifest, canonical_data_dir / "b3_agent.db"}
    inventory = []
    for directory in directories:
        if directory.is_dir():
            paths.update(directory.glob("*.sqlite3"))
            paths.update(directory.glob("*.sqlite"))
            paths.update(directory.glob("*.db"))
        notes = directory / "imports/brokerage_notes"
        inventory.append({"data_dir": str(directory), "archived_brokerage_pdfs": sum(1 for _ in notes.glob("*.pdf")) if notes.is_dir() else 0})
    databases = [inspect_database(path, sample_limit=sample_limit) for path in sorted(paths)]
    ledger = next(item for item in databases if item["path"] == str(canonical))
    table = ledger["tables"].get("option_transactions", {})
    usable = table.get("canonical_uc07_usable_rows")
    if ledger["status"] == "READ_ERROR":
        diagnosis = "CANONICAL_LEDGER_READ_ERROR"
    elif ledger["exists"]:
        diagnosis = "CANONICAL_LEDGER_READY" if usable else "CANONICAL_LEDGER_PRESENT_BUT_NO_UC07_USABLE_ROWS"
    elif any(item["exists"] and "option_transactions" in item["tables"] for item in databases):
        diagnosis = "LEDGER_EXISTS_OUTSIDE_CANONICAL_DATA_DIR"
    elif inventory[0]["archived_brokerage_pdfs"]:
        diagnosis = "CANONICAL_PDFS_PRESENT_LEDGER_MISSING"
    else:
        diagnosis = "NO_CANONICAL_LEDGER_OR_ARCHIVED_BROKERAGE_PDFS_FOUND"
    return {
        "canonical_data_dir": str(canonical_data_dir),
        "diagnosis": diagnosis,
        "canonical_uc07_usable_rows": usable,
        "database_snapshots": "consistent per database; not an atomic cross-database snapshot",
        "limitations": [
            "READ_OK/READY is inventory only, not UC-07 lifecycle acceptance.",
            "Symbol hints cannot establish PETR4 identity, strike, expiry, assignment, roll or covered state.",
            "Date range does not establish complete brokerage-note coverage.",
            "No LLM, ingestion, migration, new tables or provider calls executed.",
        ],
        "inventory": inventory,
        "databases": databases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="Override canonical runtime data directory")
    parser.add_argument("--samples", type=int, default=3, choices=range(0, 11))
    args = parser.parse_args()
    try:
        data_dir = (args.data_dir or _canonical_data_dir()).expanduser().resolve()
        report = build_report(data_dir, sample_limit=args.samples)
    except OSError as exc:
        print(json.dumps({"diagnosis": "CONFIG_READ_ERROR", "error": str(exc)}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["diagnosis"] == "CANONICAL_LEDGER_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
