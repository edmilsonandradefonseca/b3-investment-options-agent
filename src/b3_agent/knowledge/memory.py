from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .obsidian import ObsidianKnowledgeStore
from .retrieval import ObsidianRetriever, RetrievedEvidence


@dataclass(frozen=True)
class InsightRecord:
    """First-class persistent investment insight."""
    insight_id: str
    entity: str | None
    insight_type: str
    title: str
    statement: str
    evidence: tuple[str, ...] = ()
    source: str = "B3 Investment Intelligence"
    confidence: float | None = None
    created_at: datetime | None = None
    as_of: datetime | None = None
    status: str = "active"
    previous_insight_id: str | None = None

    def __post_init__(self) -> None:
        if not self.insight_id.strip():
            raise ValueError("insight_id must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.statement.strip():
            raise ValueError("statement must not be empty")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")


class ObsidianMemoryManager:
    """Application-level memory boundary over Obsidian and its RAG index."""
    def __init__(self, store: ObsidianKnowledgeStore, retriever: ObsidianRetriever | None = None) -> None:
        self.store = store
        self.retriever = retriever or ObsidianRetriever(store)

    def retrieve_context(self, query: str, *, top_k: int = 5) -> dict[str, list[dict[str, Any]]]:
        records = self.retriever.retrieve(query, top_k=top_k)
        rag_context = [self._evidence_to_dict(item) for item in records]
        return {"memory_context": list(rag_context), "rag_context": list(rag_context)}

    def persist_insight(self, insight: InsightRecord | dict[str, Any]) -> Path:
        record = self._coerce_insight(insight)
        created_at = record.created_at or datetime.now(timezone.utc)
        as_of = record.as_of or created_at
        relative_path = Path("00_System") / "Knowledge" / "Insights" / record.insight_id / "v1.md"
        evidence = "\n".join(f"- {item}" for item in record.evidence) or "- none"
        confidence = "" if record.confidence is None else str(record.confidence)
        content = f"""# {record.title}

## Metadata

- Insight ID: {record.insight_id}
- Entity: {record.entity or ""}
- Type: {record.insight_type}
- Status: {record.status}
- Source: {record.source}
- Confidence: {confidence}
- Created At: {created_at.isoformat()}
- As Of: {as_of.isoformat()}
- Previous Insight: {record.previous_insight_id or ""}

## Statement

{record.statement}

## Evidence

{evidence}
"""
        self.store.write_note(relative_path, content)
        return relative_path

    def persist_decision(self, decision: dict[str, Any], *, request: str, ticker: str | None = None) -> Path:
        decision_id = str(decision.get("id") or _stable_id("DEC"))
        subject = str(decision.get("subject_id") or ticker or "PORTFOLIO")
        action = str(decision.get("action") or "UNSPECIFIED")
        relative_path = Path("06_Decisions") / f"{decision_id}.md"
        evidence_refs = decision.get("evidence_refs") or []
        risks = decision.get("risks") or []
        content = f"""# Decision Proposal — {subject}

## Metadata

- Decision ID: {decision_id}
- Subject: {subject}
- Action: {action}
- Status: PROPOSED
- Created At: {datetime.now(timezone.utc).isoformat()}

## Request

{request}

## Thesis

{decision.get("thesis", "")}

## Rationale

{decision.get("rationale", "")}

## Evidence References

{_bullet_list(evidence_refs)}

## Risks

{_bullet_list(risks)}

## Opportunity Cost

{decision.get("opportunity_cost", "")}

## Capital Impact

{decision.get("capital_impact", "")}

## Confidence

{decision.get("confidence", "")}

## Invalidation Conditions

{_bullet_list(decision.get("invalidation_conditions") or [])}
"""
        self.store.write_note(relative_path, content)
        return relative_path

    @staticmethod
    def _evidence_to_dict(item: RetrievedEvidence) -> dict[str, Any]:
        return {"source_ref": item.source_ref, "relative_path": item.relative_path, "snippet": item.snippet, "score": item.score}

    @staticmethod
    def _coerce_insight(value: InsightRecord | dict[str, Any]) -> InsightRecord:
        if isinstance(value, InsightRecord):
            return value
        data = dict(value)
        evidence = data.get("evidence") or data.get("evidence_refs") or ()
        confidence = _normalize_confidence(data.get("confidence"))
        return InsightRecord(
            insight_id=str(data.get("insight_id") or data.get("id") or _stable_id("INS")),
            entity=data.get("entity"),
            insight_type=str(data.get("insight_type") or data.get("type") or "assessment"),
            title=str(data.get("title") or "Investment Insight"),
            statement=str(data.get("statement") or data.get("content") or ""),
            evidence=tuple(str(item) for item in evidence),
            source=str(data.get("source") or "B3 Investment Intelligence"),
            confidence=confidence,
            created_at=data.get("created_at"),
            as_of=data.get("as_of"),
            status=str(data.get("status") or "active"),
            previous_insight_id=data.get("previous_insight_id"),
        )


def _normalize_confidence(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    mapping = {"LOW": 0.25, "MEDIUM": 0.50, "HIGH": 0.75}
    text = str(value).strip().upper()
    if text in mapping:
        return mapping[text]
    raise ValueError(f"unsupported confidence value: {value}")


def _stable_id(prefix: str) -> str:
    now = datetime.now(timezone.utc)
    return f"{prefix}-{now:%Y%m%d-%H%M%S-%f}"


def _bullet_list(items: list[Any] | tuple[Any, ...]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- none"
