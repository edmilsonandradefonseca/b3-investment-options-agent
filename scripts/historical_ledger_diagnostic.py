#!/usr/bin/env python3
"""Read-only runtime inventory. Never construct repositories or initialize stores."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import pwd
import sqlite3
import subprocess
import time

RUNTIME_ENV_FILES = (Path("/etc/b3-runtime.env"), Path("/opt/b3-runtime/b3.env"))
DEFAULT_RUNTIME_DATA = Path("/opt/b3-runtime/data")
RUNTIME_PATH_KEYS = {"B3_AGENT_DATA_DIR", "B3_RUNTIME_ROOT", "B3_AGENT_PROJECT_ROOT"}
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
            if key.strip() in RUNTIME_PATH_KEYS:
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
        _invoking_home() / "b3-investment-options-agent/data",
    )
    return tuple(dict.fromkeys(path.expanduser().resolve() for path in values))


def _invoking_home() -> Path:
    """sudo changes HOME; search the invoking user's project, not /root."""
    user = os.getenv("SUDO_USER")
    if user:
        try:
            return Path(pwd.getpwnam(user).pw_dir)
        except KeyError:
            pass
    return Path.home()


def _process_paths(pid: int, proc_root: Path = Path("/proc")) -> dict | None:
    """Only admit the B3 uvicorn process, never publish its command or secrets."""
    try:
        directory = proc_root / str(pid)
        args = directory.joinpath("cmdline").read_bytes().split(b"\0")
        if b"b3_agent.server:app" not in args or b"uvicorn" not in args:
            return None
        paths = {}
        for item in directory.joinpath("environ").read_bytes().split(b"\0"):
            key, sep, value = item.partition(b"=")
            if sep and key.decode(errors="replace") in RUNTIME_PATH_KEYS:
                paths[key.decode()] = value.decode(errors="replace")
        return {"pid": pid, "paths": paths}
    except OSError:
        return None


def active_runtime_paths() -> dict:
    """Read service descendants / known runtime PID; do not start any service."""
    pending = []
    errors = []
    try:
        result = subprocess.run(
            ["systemctl", "show", "b3-runtime.service", "--property=MainPID", "--value"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            pending.append(int(result.stdout.strip()))
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(type(exc).__name__)
    roots = {DEFAULT_RUNTIME_DATA.parent}
    for file in RUNTIME_ENV_FILES:
        try:
            values = _env_file_values(file)
            if values.get("B3_RUNTIME_ROOT"):
                roots.add(Path(values["B3_RUNTIME_ROOT"]))
        except OSError as exc:
            errors.append(f"{file}: {type(exc).__name__}")
    for root in roots:
        try:
            pending.append(int((root / "orchestrator.pid").read_text().strip()))
        except (OSError, ValueError):
            pass
    visited = set()
    found = []
    while pending and len(visited) < 32:
        pid = pending.pop()
        if pid <= 0 or pid in visited:
            continue
        visited.add(pid)
        info = _process_paths(pid)
        if info:
            found.append(info)
        try:
            pending.extend(int(value) for value in Path(f"/proc/{pid}/task/{pid}/children").read_text().split())
        except (OSError, ValueError):
            pass
    return {"status": "OBSERVED" if found else "UNKNOWN", "processes": found, "errors": errors}


def discover_files(roots: tuple[Path, ...]) -> dict:
    """Bounded project-only inventory; no symlink traversal, PDF parsing or writes."""
    databases, artifacts, errors = set(), [], []
    seen = set()
    truncated = False
    excluded = {".git", ".venv", "venv", "node_modules", "__pycache__", "upstream"}
    for root in roots:
        if not root.is_dir():
            continue
        def onerror(exc):
            errors.append(f"{exc.filename}: {type(exc).__name__}")
        for parent, directories, files in os.walk(root, followlinks=False, onerror=onerror):
            path = Path(parent)
            resolved = path.resolve()
            if resolved in seen:
                directories[:] = []
                continue
            seen.add(resolved)
            if len(seen) > 10000 or len(databases) >= 100 or len(artifacts) >= 200:
                truncated = True
                break
            depth = len(path.relative_to(root).parts)
            directories[:] = sorted(d for d in directories if d not in excluded and not (path / d).is_symlink()) if depth < 8 else []
            if depth >= 8:
                truncated = True
            for name in sorted(files):
                file = path / name
                if file.is_symlink():
                    continue
                suffix = file.suffix.lower()
                if suffix in {".sqlite3", ".sqlite", ".db"}:
                    databases.add(file.resolve())
                elif suffix in {".pdf", ".zip", ".xlsx"}:
                    artifacts.append(str(file))
                if len(databases) >= 100 or len(artifacts) >= 200:
                    truncated = True
                    break
    return {"roots": [str(root) for root in roots], "databases": sorted(str(path) for path in databases), "source_file_candidates": artifacts, "truncated": truncated, "errors": errors}


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


def build_report(canonical_data_dir: Path, *, sample_limit: int = 3, extra_databases: tuple[Path, ...] = ()) -> dict:
    canonical = canonical_data_dir / "options.sqlite3"
    canonical_manifest = canonical_data_dir / "source_manifest.sqlite3"
    directories = _candidate_data_dirs(canonical_data_dir)
    paths = {canonical, canonical_manifest, canonical_data_dir / "b3_agent.db", *extra_databases}
    inventory = []
    for directory in directories:
        if directory.is_dir():
            paths.update(directory.glob("*.sqlite3"))
            paths.update(directory.glob("*.sqlite"))
            paths.update(directory.glob("*.db"))
        notes = directory / "imports/brokerage_notes"
        inventory.append({"data_dir": str(directory), "archived_brokerage_pdfs": sum(1 for _ in notes.glob("*.pdf")) if notes.is_dir() else 0})
    databases = []
    deadline = time.monotonic() + 45
    ordered = [canonical, canonical_manifest, canonical_data_dir / "b3_agent.db"]
    ordered.extend(sorted(paths - set(ordered)))
    uninspected = []
    for path in ordered:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            uninspected.append(str(path))
            continue
        databases.append(inspect_database(path, sample_limit=sample_limit, timeout_seconds=min(5, remaining)))
    ledger = next(item for item in databases if item["path"] == str(canonical))
    table = ledger["tables"].get("option_transactions", {})
    usable = table.get("canonical_uc07_usable_rows")
    if ledger["status"] == "READ_ERROR":
        diagnosis = "CANONICAL_LEDGER_READ_ERROR"
    elif ledger["exists"]:
        diagnosis = "CANONICAL_LEDGER_HAS_EXECUTIONS" if usable else "CANONICAL_LEDGER_PRESENT_BUT_NO_UC07_USABLE_ROWS"
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
        "history_coverage": "UNKNOWN",
        "lifecycle_acceptance": "NOT_VALIDATED",
        "uninspected_databases": uninspected,
        "database_snapshots": "consistent per database; not an atomic cross-database snapshot",
        "limitations": [
            "READ_OK/HAS_EXECUTIONS is inventory only, not complete history or UC-07 lifecycle acceptance.",
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
    parser.add_argument("--discover", action="store_true", help="Confirm active process paths and search bounded B3 project/runtime directories")
    parser.add_argument("--compact", action="store_true", help="Omit unrelated table schemas from output")
    args = parser.parse_args()
    try:
        runtime = active_runtime_paths() if args.discover else {"status": "NOT_CHECKED", "processes": []}
        active_dirs = {p["paths"]["B3_AGENT_DATA_DIR"] for p in runtime["processes"] if p["paths"].get("B3_AGENT_DATA_DIR")}
        active_dir = Path(next(iter(active_dirs))) if len(active_dirs) == 1 else None
        data_dir = (args.data_dir or active_dir or _canonical_data_dir()).expanduser().resolve()
        roots = {data_dir, data_dir.parent / "backups", Path("/opt/b3-investment-options-agent"), _invoking_home() / "b3-investment-options-agent"}
        for process in runtime["processes"]:
            paths = process["paths"]
            roots.update(Path(paths[key]) for key in RUNTIME_PATH_KEYS if paths.get(key))
        # Fail closed against accidentally configured broad filesystem roots.
        roots = {p.resolve() for p in roots if len(p.resolve().parts) >= 3}
        discovery = discover_files(tuple(sorted(roots))) if args.discover else {}
        report = build_report(data_dir, sample_limit=args.samples, extra_databases=tuple(Path(p) for p in discovery.get("databases", [])))
        report["runtime"] = runtime
        report["data_dir_authority"] = "EXPLICIT_OVERRIDE" if args.data_dir else "ACTIVE_B3_PROCESS" if active_dir else "CONFIGURATION_NOT_PROCESS_VERIFIED"
        if len(active_dirs) > 1:
            report["limitations"].append("Conflicting active B3 process data directories; canonical selection is not confirmed.")
        report["discovery"] = discovery
        if args.compact:
            for database in report["databases"]:
                for name, table in database["tables"].items():
                    if name not in {"option_transactions", "transactions", "source_manifest"}:
                        table.pop("schema", None)
    except OSError as exc:
        print(json.dumps({"diagnosis": "CONFIG_READ_ERROR", "error": str(exc)}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["diagnosis"] == "CANONICAL_LEDGER_HAS_EXECUTIONS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
