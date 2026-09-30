from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from b3_agent.config import settings
from b3_agent.llm.host_lock import LocalReasoningBusy
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.intelligence.relevance_screen import (
    LocalRelevanceAnalyst,
    LocalRelevanceQueue,
    promote_to_dossier,
)


class LocalRelevanceScreenJob:
    """Cheap first-stage local screen; promotes only relevant candidates."""

    def __init__(
        self,
        *,
        queue: LocalRelevanceQueue | None = None,
        analyst: LocalRelevanceAnalyst | None = None,
        dossier_queue: LocalEvidenceQueue | None = None,
        output_root: str | Path | None = None,
    ) -> None:
        root = Path(
            output_root
            or settings.data_dir / "derived" / "local_relevance_screen"
        )
        self.queue = queue or LocalRelevanceQueue(root)
        self.analyst = analyst or LocalRelevanceAnalyst()
        self.dossier_queue = dossier_queue or LocalEvidenceQueue(
            settings.data_dir / "derived" / "local_evidence_analyst"
        )

    def run(self, *, limit: int = 5) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        requests = self.queue.pending(limit=limit)
        results: list[dict[str, Any]] = []

        for request in requests:
            self.queue.mark_running(request)
            try:
                result = self.analyst.analyze(request)
                self.queue.complete(result)
                promotion = promote_to_dossier(
                    request,
                    result,
                    self.dossier_queue,
                )
                results.append(
                    {
                        "request_id": result.request_id,
                        "ticker": result.ticker,
                        "status": result.status.value,
                        "relevance": (
                            result.screen.get("relevance")
                            if result.screen
                            else None
                        ),
                        "quality_flags": list(result.quality_flags),
                        "dossier_queue_status": promotion,
                    }
                )
            except LocalReasoningBusy as exc:
                self.queue.defer(request, reason=str(exc))
                results.append(
                    {
                        "request_id": request.request_id,
                        "ticker": request.ticker,
                        "status": "DEFERRED",
                        "relevance": None,
                        "quality_flags": ["LOCAL_REASONING_BUSY"],
                        "dossier_queue_status": "NOT_PROMOTED",
                    }
                )
            except Exception as exc:
                result = self.queue.fail(
                    request,
                    error=f"{type(exc).__name__}: {exc}",
                    model=getattr(self.analyst.client, "model", "unknown"),
                )
                results.append(
                    {
                        "request_id": result.request_id,
                        "ticker": result.ticker,
                        "status": result.status.value,
                        "relevance": None,
                        "quality_flags": list(result.quality_flags),
                        "dossier_queue_status": "NOT_PROMOTED",
                    }
                )

        manifest = {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "started_at": started_at.isoformat(),
            "requested_limit": limit,
            "processed": len(results),
            "ready": sum(item["status"] == "READY" for item in results),
            "degraded": sum(item["status"] == "DEGRADED" for item in results),
            "failed": sum(item["status"] == "FAILED" for item in results),
            "deferred": sum(item["status"] == "DEFERRED" for item in results),
            "promoted": sum(
                item["dossier_queue_status"]
                in {"ENQUEUED", "ALREADY_QUEUED", "ALREADY_PROCESSED"}
                for item in results
            ),
            "remaining_queue": len(self.queue.pending()),
            "results": results,
        }
        path = self.queue.manifests_dir / "latest.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(path)
        return manifest
