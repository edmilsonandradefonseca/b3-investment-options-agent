#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from b3_agent.config import settings
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.repositories.source_manifest import SourceManifestRepository


def _candidate_data_dirs() -> tuple[Path, ...]:
    repo_root = Path(__file__).resolve().parent.parent
    values = [
        settings.data_dir,
        repo_root / "data",
        Path("/opt/b3-runtime/data"),
        Path("/opt/b3-investment-options-agent/data"),
        Path.home() / "b3-investment-options-agent" / "data",
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for value in values:
        resolved = value.expanduser().resolve()
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return tuple(unique)


def _sqlite_row_count(path: Path, table: str) -> int | None:
    if not path.is_file():
        return None
    try:
        with sqlite3.connect(path) as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            return int(row[0]) if row else 0
    except sqlite3.Error:
        return None


def main() -> int:
    print("===== B3 HISTORICAL LEDGER DIAGNOSTIC =====")
    print(f"settings.data_dir={settings.data_dir}")
    print(f"B3_AGENT_DATA_DIR={os.getenv('B3_AGENT_DATA_DIR') or '<unset>'}")
    print()

    canonical = settings.data_dir / "options.sqlite3"
    canonical_manifest = settings.data_dir / "source_manifest.sqlite3"

    for data_dir in _candidate_data_dirs():
        ledger = data_dir / "options.sqlite3"
        manifest = data_dir / "source_manifest.sqlite3"
        notes_dir = data_dir / "imports" / "brokerage_notes"
        options_xlsx = data_dir / "imports" / "options_transactions.xlsx"

        ledger_count = _sqlite_row_count(ledger, "option_transactions")
        manifest_count = _sqlite_row_count(manifest, "source_manifest")
        pdf_count = len(tuple(notes_dir.glob("*.pdf"))) if notes_dir.is_dir() else 0

        print(f"DATA_DIR {data_dir}")
        print(f"  ledger_exists={ledger.is_file()} ledger_rows={ledger_count}")
        print(f"  manifest_exists={manifest.is_file()} manifest_rows={manifest_count}")
        print(f"  archived_brokerage_pdfs={pdf_count}")
        print(f"  options_transactions_xlsx={options_xlsx.is_file()}")

        if ledger.is_file():
            try:
                rows = OptionTransactionLedger(ledger).list_all()
                dated = sum(1 for row in rows if row.as_of is not None)
                priced = sum(1 for row in rows if row.execution_price is not None)
                source_types = sorted({row.source_type for row in rows})
                dates = sorted(row.as_of for row in rows if row.as_of is not None)
                print(
                    "  ledger_quality="
                    f"dated={dated}/{len(rows)} priced={priced}/{len(rows)} "
                    f"source_types={source_types}"
                )
                if dates:
                    print(f"  coverage={dates[0]}..{dates[-1]}")
            except Exception as exc:
                print(f"  ledger_read_error={type(exc).__name__}: {exc}")

        if manifest.is_file():
            try:
                records = SourceManifestRepository(manifest).list_all()
                note_records = [item for item in records if item.source_type == "BROKERAGE_NOTE"]
                print(f"  brokerage_note_manifest_rows={len(note_records)}")
                if note_records:
                    starts = [item.coverage_start for item in note_records if item.coverage_start]
                    ends = [item.coverage_end for item in note_records if item.coverage_end]
                    total_records = sum(item.record_count for item in note_records)
                    print(f"  brokerage_note_manifest_records={total_records}")
                    if starts and ends:
                        print(f"  brokerage_note_manifest_coverage={min(starts)}..{max(ends)}")
            except Exception as exc:
                print(f"  manifest_read_error={type(exc).__name__}: {exc}")
        print()

    print("===== CANONICAL EXPECTATION =====")
    print(f"canonical_ledger={canonical}")
    print(f"canonical_manifest={canonical_manifest}")

    if canonical.is_file():
        rows = OptionTransactionLedger(canonical).list_all()
        usable = [
            row
            for row in rows
            if row.as_of is not None and row.execution_price is not None
        ]
        print(f"canonical_rows={len(rows)}")
        print(f"canonical_uc07_usable_rows={len(usable)}")
        if usable:
            print("DIAGNOSIS=CANONICAL_LEDGER_READY")
            return 0
        print("DIAGNOSIS=CANONICAL_LEDGER_PRESENT_BUT_NO_UC07_USABLE_ROWS")
        return 2

    other_ledgers = [
        data_dir / "options.sqlite3"
        for data_dir in _candidate_data_dirs()
        if data_dir != settings.data_dir and (data_dir / "options.sqlite3").is_file()
    ]
    canonical_pdfs = settings.data_dir / "imports" / "brokerage_notes"
    if other_ledgers:
        print("DIAGNOSIS=LEDGER_EXISTS_OUTSIDE_CANONICAL_DATA_DIR")
        for item in other_ledgers:
            print(f"candidate_ledger={item}")
        return 3
    if canonical_pdfs.is_dir() and any(canonical_pdfs.glob("*.pdf")):
        print("DIAGNOSIS=CANONICAL_PDFS_PRESENT_LEDGER_MISSING")
        return 4

    print("DIAGNOSIS=NO_CANONICAL_LEDGER_OR_ARCHIVED_BROKERAGE_PDFS_FOUND")
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
