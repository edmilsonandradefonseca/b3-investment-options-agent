from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from b3_agent.config import settings
from b3_agent.intelligence.continuous_triage import (
    ContinuousTriageAction,
    canonical_evidence_fingerprint,
    triage_official_evidence,
)
from b3_agent.intelligence.discovery_cursor import DiscoveryCursorStore
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.intelligence.official_evidence import (
    OfficialEvidenceBuilder,
    evidence_to_dict,
)
from b3_agent.intelligence.relevance_screen import LocalRelevanceQueue
from b3_agent.knowledge.evidence import Evidence
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.providers.cvm_rad import CvmRadDisclosureProvider


class ContinuousIntelligenceJob:
    """Incremental CVM discovery with no inline LLM inference."""

    def __init__(
        self,
        *,
        provider: CvmRadDisclosureProvider | None = None,
        registry: IssuerRegistry | None = None,
        cursor_store: DiscoveryCursorStore | None = None,
        dossier_queue: LocalEvidenceQueue | None = None,
        relevance_queue: LocalRelevanceQueue | None = None,
        root: str | Path | None = None,
    ) -> None:
        self.root = Path(
            root or settings.data_dir / "derived" / "continuous_intelligence"
        )
        self.root.mkdir(parents=True, exist_ok=True)
        overlap = int(os.getenv("B3_INTEL_CURSOR_OVERLAP_MINUTES", "30"))
        initial_hours = int(os.getenv("B3_INTEL_INITIAL_LOOKBACK_HOURS", "24"))
        self.provider = provider or CvmRadDisclosureProvider()
        self.registry = registry or IssuerRegistry()
        self.builder = OfficialEvidenceBuilder(registry=self.registry)
        self.cursor_store = cursor_store or DiscoveryCursorStore(
            settings.data_dir / "structured" / "cvm_rad_discovery_cursor.json",
            overlap_minutes=overlap,
            initial_lookback_hours=initial_hours,
        )
        self.dossier_queue = dossier_queue or LocalEvidenceQueue(
            settings.data_dir / "derived" / "local_evidence_analyst"
        )
        self.relevance_queue = relevance_queue or LocalRelevanceQueue(
            settings.data_dir / "derived" / "local_relevance_screen"
        )
        self.evidence_dir = self.root / "evidence"
        self.runs_dir = self.root / "runs"

    def run(
        self,
        *,
        now: datetime | None = None,
        monitored_tickers: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        local_now = now or datetime.now(ZoneInfo(settings.timezone))
        if local_now.tzinfo is None or local_now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        monitored = tuple(
            dict.fromkeys(
                ticker.upper().strip()
                for ticker in (
                    monitored_tickers
                    if monitored_tickers is not None
                    else _monitored_tickers()
                )
                if ticker.strip()
            )
        )

        state = self.cursor_store.load()
        start, end = self.cursor_store.query_window(now=local_now, state=state)
        processed_before = set(state.processed_evidence_keys)
        provider_ids: list[str] = []
        completed_keys: list[str] = []
        query_summaries: list[dict[str, Any]] = []
        metrics = {
            "documents": 0,
            "new_evidence": 0,
            "duplicates": 0,
            "mapped": 0,
            "material": 0,
            "candidate": 0,
            "non_material": 0,
            "dossier_enqueued": 0,
            "relevance_enqueued": 0,
            "skipped": 0,
        }
        triage_rows: list[dict[str, Any]] = []

        try:
            for day in _dates_between(start.date(), end.date()):
                requested_time = (
                    start.strftime("%H:%M")
                    if day == start.date()
                    else "00:00"
                )
                result = self.provider.query_ipe(
                    day,
                    requested_time=requested_time,
                )
                query_summaries.append(
                    {
                        "date": day.isoformat(),
                        "requested_time": requested_time,
                        "source_error_code": result.source_error_code,
                        "documents": len(result.disclosures),
                    }
                )
                for disclosure in result.disclosures:
                    metrics["documents"] += 1
                    provider_ids.append(disclosure.provider_record_id)
                    evidence = self.builder.from_rad(disclosure)
                    key = canonical_evidence_fingerprint(evidence)
                    persisted = self._persist_evidence(key, evidence)
                    if persisted:
                        metrics["new_evidence"] += 1
                    else:
                        metrics["duplicates"] += 1

                    if evidence.metadata.ticker_refs:
                        metrics["mapped"] += 1
                    materiality = evidence.metadata.materiality
                    if materiality == "MATERIAL":
                        metrics["material"] += 1
                    elif materiality == "CANDIDATE":
                        metrics["candidate"] += 1
                    else:
                        metrics["non_material"] += 1

                    if key in processed_before:
                        metrics["skipped"] += 1
                        triage_rows.append(
                            {
                                "evidence_key": key,
                                "evidence_id": evidence.evidence_id,
                                "action": "SKIP",
                                "reason": "ALREADY_PROCESSED",
                            }
                        )
                        continue

                    decision = triage_official_evidence(
                        evidence,
                        monitored_tickers=monitored,
                        as_of=local_now,
                    )
                    event = _official_event(evidence)
                    queue_statuses: list[str] = []
                    if decision.action == ContinuousTriageAction.DOSSIER:
                        for ticker in decision.tickers:
                            enqueue = self.dossier_queue.enqueue(ticker, [event])
                            queue_statuses.append(enqueue.queue_status)
                            if enqueue.queue_status == "ENQUEUED":
                                metrics["dossier_enqueued"] += 1
                    elif decision.action == ContinuousTriageAction.RELEVANCE_SCREEN:
                        for ticker in decision.tickers:
                            _, status = self.relevance_queue.enqueue(ticker, [event])
                            queue_statuses.append(status)
                            if status == "ENQUEUED":
                                metrics["relevance_enqueued"] += 1
                    else:
                        metrics["skipped"] += 1

                    triage_rows.append(
                        {
                            "evidence_key": key,
                            "evidence_id": evidence.evidence_id,
                            "action": decision.action.value,
                            "reason": decision.reason,
                            "tickers": list(decision.tickers),
                            "queue_statuses": queue_statuses,
                        }
                    )
                    completed_keys.append(key)

            completed_at = datetime.now(local_now.tzinfo)
            new_state = self.cursor_store.commit_success(
                requested_through=end,
                retrieval_at=completed_at,
                provider_ids=provider_ids,
                processed_evidence_keys=completed_keys,
                previous=state,
            )
        except Exception as exc:
            self.cursor_store.record_error(
                f"{type(exc).__name__}: {exc}",
                previous=state,
            )
            raise

        manifest = {
            "status": "PASS",
            "source": "CVM_RAD",
            "started_from": start.isoformat(),
            "requested_through": end.isoformat(),
            "completed_at": completed_at.isoformat(),
            "monitored_tickers": list(monitored),
            "deepseek_called_inline": False,
            "cursor": new_state.as_dict(),
            "queries": query_summaries,
            "metrics": metrics,
            "triage": triage_rows,
        }
        self._persist_manifest(manifest, completed_at)
        return manifest

    def _persist_evidence(self, key: str, evidence: Evidence) -> bool:
        path = self.evidence_dir / f"{key}.json"
        if path.exists():
            return False
        _atomic_json_write(
            path,
            {
                "evidence_key": key,
                "evidence": evidence_to_dict(evidence),
            },
        )
        return True

    def _persist_manifest(
        self,
        manifest: dict[str, Any],
        completed_at: datetime,
    ) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        stamp = completed_at.strftime("%Y%m%dT%H%M%S%f%z")
        _atomic_json_write(self.runs_dir / f"{stamp}.json", manifest)
        _atomic_json_write(self.root / "latest.json", manifest)


def _monitored_tickers() -> tuple[str, ...]:
    from b3_agent.intelligence.collection_universe import CollectionUniverseStore

    return CollectionUniverseStore(settings.data_dir).effective_tickers()

def _official_event(evidence: Evidence) -> dict[str, Any]:
    metadata = evidence.metadata
    return {
        "evidence_type": "official_disclosure",
        "evidence_id": evidence.evidence_id,
        "ticker_refs": list(metadata.ticker_refs),
        "issuer_ref": metadata.issuer_ref,
        "cvm_code": metadata.cvm_code,
        "published_at": (
            metadata.published_at.isoformat()
            if metadata.published_at
            else None
        ),
        "reference_at": (
            metadata.reference_at.isoformat()
            if metadata.reference_at
            else None
        ),
        "headline": evidence.title,
        "summary": evidence.content,
        "source_name": metadata.source,
        "source_ref": evidence.source_url or evidence.evidence_id,
        "materiality": metadata.materiality,
        "materiality_reason": metadata.materiality_reason,
        "pit_status": metadata.pit_status,
    }


def _dates_between(start: date, end: date) -> tuple[date, ...]:
    if end < start:
        raise ValueError("end date must not precede start date")
    days = (end - start).days
    return tuple(start + timedelta(days=offset) for offset in range(days + 1))


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temp.replace(path)
