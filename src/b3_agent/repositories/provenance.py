from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import sqlite3

from b3_agent.schemas.provenance import (
    Claim,
    ClaimEvidenceDirection,
    ClaimEvidenceLink,
    ClaimStatus,
    SourceDocument,
)
from b3_agent.storage.sqlite import SQLiteStore


class ProvenanceRepository:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def save_document(self, item: SourceDocument) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO source_documents
                (document_id, source, title, retrieved_at, published_at, source_url, content_hash, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (item.document_id, item.source, item.title, item.retrieved_at.isoformat(),
                 item.published_at.isoformat() if item.published_at else None,
                 item.source_url, item.content_hash, item.version),
            )

    def save_claim(self, item: Claim) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO claims
                (claim_id, statement, created_at, status, valid_from, valid_to, version, supersedes_claim_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (item.claim_id, item.statement, item.created_at.isoformat(), item.status.value,
                 item.valid_from.isoformat() if item.valid_from else None,
                 item.valid_to.isoformat() if item.valid_to else None,
                 item.version, item.supersedes_claim_id),
            )

    def link(self, item: ClaimEvidenceLink) -> None:
        with self.store.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO claim_evidence_links
                (claim_id, evidence_id, document_id, direction, observed_at, confidence)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (item.claim_id, item.evidence_id, item.document_id, item.direction.value,
                 item.observed_at.isoformat(), item.confidence),
            )

    def evidence_for_claim(self, claim_id: str) -> tuple[ClaimEvidenceLink, ...]:
        with self.store.connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM claim_evidence_links WHERE claim_id=? ORDER BY observed_at, evidence_id",
                (claim_id,),
            ).fetchall()
        return tuple(
            ClaimEvidenceLink(
                claim_id=row["claim_id"], evidence_id=row["evidence_id"],
                document_id=row["document_id"],
                direction=ClaimEvidenceDirection(row["direction"]),
                observed_at=datetime.fromisoformat(row["observed_at"]),
                confidence=float(row["confidence"]),
            ) for row in rows
        )
