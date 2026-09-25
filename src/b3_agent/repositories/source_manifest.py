from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class SourceManifestRecord:
    """Audit record describing the scope of an imported transaction source."""

    source_fingerprint: str
    source_type: str
    source_id: str
    source_ref: str
    file_name: str
    imported_at: datetime
    record_count: int
    coverage_start: date | None = None
    coverage_end: date | None = None
    scope: str = "PERIOD_ONLY"
    completeness: str = "UNKNOWN"


class SourceManifestRepository:
    """Persistent manifest for transaction-source ingestion and coverage evidence."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_manifest (
                    source_fingerprint TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    coverage_start TEXT,
                    coverage_end TEXT,
                    scope TEXT NOT NULL DEFAULT 'PERIOD_ONLY',
                    completeness TEXT NOT NULL DEFAULT 'UNKNOWN'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_manifest_type ON source_manifest(source_type)"
            )
            conn.commit()

    def upsert(self, record: SourceManifestRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO source_manifest (
                    source_fingerprint, source_type, source_id, source_ref,
                    file_name, imported_at, record_count, coverage_start,
                    coverage_end, scope, completeness
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_fingerprint) DO UPDATE SET
                    source_type=excluded.source_type,
                    source_id=excluded.source_id,
                    source_ref=excluded.source_ref,
                    file_name=excluded.file_name,
                    imported_at=excluded.imported_at,
                    record_count=excluded.record_count,
                    coverage_start=excluded.coverage_start,
                    coverage_end=excluded.coverage_end,
                    scope=excluded.scope,
                    completeness=excluded.completeness
                """,
                (
                    record.source_fingerprint,
                    record.source_type,
                    record.source_id,
                    record.source_ref,
                    record.file_name,
                    record.imported_at.isoformat(),
                    record.record_count,
                    record.coverage_start.isoformat() if record.coverage_start else None,
                    record.coverage_end.isoformat() if record.coverage_end else None,
                    record.scope,
                    record.completeness,
                ),
            )
            conn.commit()

    def list_all(self) -> tuple[SourceManifestRecord, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT source_fingerprint, source_type, source_id, source_ref,
                       file_name, imported_at, record_count, coverage_start,
                       coverage_end, scope, completeness
                FROM source_manifest
                ORDER BY imported_at DESC
                """
            ).fetchall()

        return tuple(
            SourceManifestRecord(
                source_fingerprint=row[0],
                source_type=row[1],
                source_id=row[2],
                source_ref=row[3],
                file_name=row[4],
                imported_at=datetime.fromisoformat(row[5]),
                record_count=row[6],
                coverage_start=date.fromisoformat(row[7]) if row[7] else None,
                coverage_end=date.fromisoformat(row[8]) if row[8] else None,
                scope=row[9],
                completeness=row[10],
            )
            for row in rows
        )
