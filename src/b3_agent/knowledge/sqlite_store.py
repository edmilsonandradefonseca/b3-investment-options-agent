from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import KnowledgeRecord


class B3KnowledgeStore:
    """Canonical SQLite knowledge store for B3 knowledge."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_records (
                    knowledge_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    content TEXT NOT NULL,
                    validated_at TEXT,
                    validated_by TEXT,
                    previous_version TEXT,
                    as_of TEXT,
                    retention_class TEXT NOT NULL DEFAULT 'knowledge',
                    retention_until TEXT,
                    archived_at TEXT,
                    PRIMARY KEY (knowledge_id, version)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_updated_at
                ON knowledge_records(updated_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_retention
                ON knowledge_records(retention_until)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_category
                ON knowledge_records(category)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_as_of
                ON knowledge_records(as_of)
            """)

    def record_discovery(
        self,
        record: KnowledgeRecord,
        *,
        as_of: datetime | None = None,
        retention_class: str = "knowledge",
        retention_days: int | None = 365,
    ) -> tuple[str, str]:
        if not record.knowledge_id.strip():
            raise ValueError("knowledge_id must not be empty")

        if not record.version.strip():
            raise ValueError("version must not be empty")

        if retention_days is not None and retention_days < 0:
            raise ValueError("retention_days must be >= 0 or None")

        effective_as_of = as_of or record.updated_at

        retention_until = None
        if retention_days is not None:
            retention_until = (
                effective_as_of + timedelta(days=retention_days)
            ).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_records (
                    knowledge_id,
                    version,
                    topic,
                    category,
                    status,
                    created_at,
                    updated_at,
                    source,
                    evidence,
                    content,
                    validated_at,
                    validated_by,
                    previous_version,
                    as_of,
                    retention_class,
                    retention_until
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.knowledge_id,
                    record.version,
                    record.topic,
                    record.category,
                    record.status,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    record.source,
                    record.evidence,
                    record.content,
                    (
                        record.validated_at.isoformat()
                        if record.validated_at
                        else None
                    ),
                    record.validated_by,
                    record.previous_version,
                    effective_as_of.isoformat(),
                    retention_class,
                    retention_until,
                ),
            )

        return record.knowledge_id, record.version

    def get(
        self,
        knowledge_id: str,
        version: str | None = None,
    ) -> KnowledgeRecord | None:
        with self._connect() as conn:
            if version is None:
                row = conn.execute(
                    """
                    SELECT *
                    FROM knowledge_records
                    WHERE knowledge_id = ?
                      AND archived_at IS NULL
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (knowledge_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT *
                    FROM knowledge_records
                    WHERE knowledge_id = ?
                      AND version = ?
                      AND archived_at IS NULL
                    """,
                    (knowledge_id, version),
                ).fetchone()

        return self._row_to_record(row) if row else None

    def list(self, limit: int = 100) -> list[KnowledgeRecord]:
        if limit <= 0:
            raise ValueError("limit must be positive")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM knowledge_records
                WHERE archived_at IS NULL
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [self._row_to_record(row) for row in rows]

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[KnowledgeRecord]:
        if not query.strip():
            raise ValueError("query must not be empty")

        if limit <= 0:
            raise ValueError("limit must be positive")

        pattern = f"%{query}%"

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM knowledge_records
                WHERE archived_at IS NULL
                  AND (
                       topic LIKE ?
                    OR category LIKE ?
                    OR source LIKE ?
                    OR evidence LIKE ?
                    OR content LIKE ?
                  )
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    limit,
                ),
            ).fetchall()

        return [self._row_to_record(row) for row in rows]

    def delete(self, knowledge_id: str, version: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM knowledge_records
                WHERE knowledge_id = ?
                  AND version = ?
                """,
                (knowledge_id, version),
            )

    def retention_candidates(self) -> list[sqlite3.Row]:
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM knowledge_records
                WHERE retention_until IS NOT NULL
                  AND retention_until < ?
                  AND archived_at IS NULL
                ORDER BY retention_until
                """,
                (now,),
            ).fetchall()

    def archive(
        self,
        knowledge_id: str,
        version: str,
    ) -> None:
        archived_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE knowledge_records
                SET archived_at = ?
                WHERE knowledge_id = ?
                  AND version = ?
                """,
                (
                    archived_at,
                    knowledge_id,
                    version,
                ),
            )

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM knowledge_records
                WHERE archived_at IS NULL
                """
            ).fetchone()

        return int(row["total"])

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> KnowledgeRecord:
        def dt(value: str | None) -> datetime | None:
            return datetime.fromisoformat(value) if value else None

        return KnowledgeRecord(
            knowledge_id=row["knowledge_id"],
            topic=row["topic"],
            category=row["category"],
            status=row["status"],
            version=row["version"],
            created_at=dt(row["created_at"]),
            updated_at=dt(row["updated_at"]),
            source=row["source"],
            evidence=row["evidence"],
            content=row["content"],
            validated_at=dt(row["validated_at"]),
            validated_by=row["validated_by"],
            previous_version=row["previous_version"],
        )
