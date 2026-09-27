from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json

from b3_agent.schemas.experience import ExperienceRetrievalResult, RetrievalTrace
from b3_agent.storage.sqlite import SQLiteStore


class RetrievalTraceRepository:
    """Persist retrieval/reranking traces for audit and evaluation."""

    def __init__(self, store: SQLiteStore):
        self.store = store

    def save(self, retrieval: ExperienceRetrievalResult) -> None:
        trace = retrieval.trace
        if trace is None:
            raise ValueError("retrieval result has no trace")

        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO retrieval_traces (
                    trace_id,
                    query_id,
                    as_of,
                    retrieval_mode,
                    fusion_method,
                    ranker_version,
                    candidate_count,
                    selected_count,
                    subject_ids_json,
                    current_snapshot_id,
                    current_regime_id,
                    retrieval_metadata_json,
                    trace_items_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trace_id) DO UPDATE SET
                    query_id = excluded.query_id,
                    as_of = excluded.as_of,
                    retrieval_mode = excluded.retrieval_mode,
                    fusion_method = excluded.fusion_method,
                    ranker_version = excluded.ranker_version,
                    candidate_count = excluded.candidate_count,
                    selected_count = excluded.selected_count,
                    subject_ids_json = excluded.subject_ids_json,
                    current_snapshot_id = excluded.current_snapshot_id,
                    current_regime_id = excluded.current_regime_id,
                    retrieval_metadata_json = excluded.retrieval_metadata_json,
                    trace_items_json = excluded.trace_items_json
                """,
                (
                    trace.trace_id,
                    retrieval.query_id,
                    retrieval.as_of.isoformat(),
                    trace.retrieval_mode,
                    trace.fusion_method,
                    trace.ranker_version,
                    trace.candidate_count,
                    trace.selected_count,
                    json.dumps(retrieval.subject_ids),
                    retrieval.current_snapshot_id,
                    retrieval.current_regime_id,
                    json.dumps(dict(retrieval.retrieval_metadata), sort_keys=True),
                    json.dumps([asdict(item) for item in trace.items], sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def get(self, trace_id: str) -> dict[str, object] | None:
        with self.store.connect() as connection:
            connection.row_factory = __import__("sqlite3").Row
            row = connection.execute(
                "SELECT * FROM retrieval_traces WHERE trace_id = ?",
                (trace_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        for field in (
            "subject_ids_json",
            "retrieval_metadata_json",
            "trace_items_json",
        ):
            result[field.removesuffix("_json")] = json.loads(result.pop(field))
        return result

    def list_recent(self, *, limit: int = 20) -> tuple[dict[str, object], ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self.store.connect() as connection:
            connection.row_factory = __import__("sqlite3").Row
            rows = connection.execute(
                """
                SELECT * FROM retrieval_traces
                ORDER BY as_of DESC, trace_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            for field in (
                "subject_ids_json",
                "retrieval_metadata_json",
                "trace_items_json",
            ):
                item[field.removesuffix("_json")] = json.loads(item.pop(field))
            result.append(item)
        return tuple(result)
