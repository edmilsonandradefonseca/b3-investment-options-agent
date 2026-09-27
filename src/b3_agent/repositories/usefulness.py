from __future__ import annotations

from datetime import datetime
import sqlite3

from b3_agent.schemas.usefulness import (
    DecisionEvidenceOutcomeAttribution,
    OutcomeAssociation,
)
from b3_agent.storage.sqlite import SQLiteStore


class UsefulnessAttributionRepository:
    """Canonical persistence for decision/evidence/outcome association observations."""

    def __init__(self, store: SQLiteStore):
        self.store = store

    def save(self, item: DecisionEvidenceOutcomeAttribution) -> None:
        import json

        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO usefulness_attributions (
                    attribution_id, decision_id, evidence_ref, outcome_id,
                    observed_at, association, attribution_confidence,
                    rationale, source_refs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(attribution_id) DO UPDATE SET
                    decision_id=excluded.decision_id,
                    evidence_ref=excluded.evidence_ref,
                    outcome_id=excluded.outcome_id,
                    observed_at=excluded.observed_at,
                    association=excluded.association,
                    attribution_confidence=excluded.attribution_confidence,
                    rationale=excluded.rationale,
                    source_refs_json=excluded.source_refs_json
                """,
                (
                    item.attribution_id, item.decision_id, item.evidence_ref,
                    item.outcome_id, item.observed_at.isoformat(),
                    item.association.value, item.attribution_confidence,
                    item.rationale, json.dumps(item.source_refs),
                ),
            )

    def list_for_evidence(
        self, evidence_ref: str
    ) -> tuple[DecisionEvidenceOutcomeAttribution, ...]:
        import json

        with self.store.connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT * FROM usefulness_attributions
                WHERE evidence_ref = ?
                ORDER BY observed_at, attribution_id
                """,
                (evidence_ref,),
            ).fetchall()
        return tuple(
            DecisionEvidenceOutcomeAttribution(
                attribution_id=row["attribution_id"],
                decision_id=row["decision_id"],
                evidence_ref=row["evidence_ref"],
                outcome_id=row["outcome_id"],
                observed_at=datetime.fromisoformat(row["observed_at"]),
                association=OutcomeAssociation(row["association"]),
                attribution_confidence=float(row["attribution_confidence"]),
                rationale=row["rationale"] or "",
                source_refs=tuple(json.loads(row["source_refs_json"])),
            )
            for row in rows
        )

    def scores(self, engine) -> dict[str, float]:
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT evidence_ref FROM usefulness_attributions"
            ).fetchall()
        return {
            row[0]: engine.assess(row[0], self.list_for_evidence(row[0])).usefulness_score
            for row in rows
        }
