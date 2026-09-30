from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from b3_agent.config import settings


def local_intelligence_status(data_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(data_dir or settings.data_dir)
    continuous = root / "derived" / "continuous_intelligence"
    relevance = root / "derived" / "local_relevance_screen"
    dossier = root / "derived" / "local_evidence_analyst"
    cursor_path = root / "structured" / "cvm_rad_discovery_cursor.json"
    reconciliation = root / "derived" / "cvm_reconciliation"

    cursor = _read_json(cursor_path)
    continuous_manifest = _read_json(continuous / "latest.json")
    relevance_manifest = _read_json(relevance / "manifests" / "latest.json")
    dossier_manifest = _read_json(dossier / "manifests" / "latest.json")
    reconciliation_manifest = _read_json(reconciliation / "latest.json")

    return {
        "status": "OK",
        "cursor": {
            "last_successful_requested_at": cursor.get("last_successful_requested_at"),
            "last_successful_retrieval_at": cursor.get("last_successful_retrieval_at"),
            "last_source_error": cursor.get("last_source_error"),
            "overlap_minutes": cursor.get("overlap_minutes"),
        },
        "queues": {
            "relevance_pending": _count_json(relevance / "queue"),
            "dossier_pending": _count_json(dossier / "queue"),
        },
        "latest": {
            "discovery": _manifest_summary(continuous_manifest),
            "relevance": _manifest_summary(relevance_manifest),
            "dossier": _manifest_summary(dossier_manifest),
            "reconciliation": _manifest_summary(reconciliation_manifest),
        },
    }


def local_intelligence_queues(data_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(data_dir or settings.data_dir)
    relevance = root / "derived" / "local_relevance_screen" / "queue"
    dossier = root / "derived" / "local_evidence_analyst" / "queue"
    return {
        "relevance": _queue_items(relevance),
        "dossier": _queue_items(dossier),
    }


def local_ticker_intelligence(
    ticker: str,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    normalized = ticker.upper().strip()
    root = Path(data_dir or settings.data_dir)
    dossier_path = (
        root / "derived" / "local_evidence_analyst" / "latest" / f"{normalized}.json"
    )
    dossier = _read_json(dossier_path)
    relevance_runs = root / "derived" / "local_relevance_screen" / "runs"
    latest_relevance = None
    if relevance_runs.is_dir():
        candidates = []
        for path in relevance_runs.glob("*.json"):
            payload = _read_json(path)
            if str(payload.get("ticker") or "").upper() == normalized:
                candidates.append((str(payload.get("created_at") or ""), payload))
        if candidates:
            latest_relevance = max(candidates, key=lambda item: item[0])[1]

    return {
        "ticker": normalized,
        "dossier": dossier or None,
        "relevance": latest_relevance,
    }


def local_intelligence_manifests(
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(data_dir or settings.data_dir)
    return {
        "discovery": _read_json(
            root / "derived" / "continuous_intelligence" / "latest.json"
        ) or None,
        "relevance": _read_json(
            root / "derived" / "local_relevance_screen" / "manifests" / "latest.json"
        ) or None,
        "dossier": _read_json(
            root / "derived" / "local_evidence_analyst" / "manifests" / "latest.json"
        ) or None,
        "reconciliation": _read_json(
            root / "derived" / "cvm_reconciliation" / "latest.json"
        ) or None,
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _count_json(path: Path) -> int:
    return len(list(path.glob("*.json"))) if path.is_dir() else 0


def _queue_items(path: Path) -> list[dict[str, Any]]:
    if not path.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for item in sorted(path.glob("*.json")):
        payload = _read_json(item)
        rows.append(
            {
                "id": payload.get("request_id") or payload.get("analysis_id") or item.stem,
                "ticker": payload.get("ticker"),
                "status": payload.get("status"),
                "created_at": payload.get("created_at"),
            }
        )
    return rows


def _manifest_summary(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not payload:
        return None
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    return {
        "status": payload.get("status"),
        "as_of": payload.get("as_of") or payload.get("completed_at"),
        "processed": payload.get("processed"),
        "remaining_queue": payload.get("remaining_queue"),
        "documents": metrics.get("documents"),
        "new_evidence": metrics.get("new_evidence"),
        "last_source_error": (
            payload.get("cursor", {}).get("last_source_error")
            if isinstance(payload.get("cursor"), dict)
            else None
        ),
    }
