from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from b3_agent.config import settings
from b3_agent.intelligence.local_evidence_analysis import (
    LocalEvidenceAnalyst,
    LocalEvidenceQueue,
)


class LocalEvidenceAnalystJob:
    """Consume queued V4.3 local Evidence analysis requests sequentially."""

    def __init__(
        self,
        *,
        queue: LocalEvidenceQueue | None = None,
        analyst: LocalEvidenceAnalyst | None = None,
        output_root: str | Path | None = None,
    ) -> None:
        root = Path(
            output_root
            or settings.data_dir / "derived" / "local_evidence_analyst"
        )
        self.queue = queue or LocalEvidenceQueue(root)
        self.analyst = analyst or LocalEvidenceAnalyst()

    def run(self, *, limit: int = 5) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        requests = self.queue.pending(limit=limit)
        results: list[dict[str, Any]] = []

        for request in requests:
            self.queue.mark_running(request)
            try:
                dossier = self.analyst.analyze(request)
                self.queue.complete(dossier)
                results.append(
                    {
                        "analysis_id": dossier.analysis_id,
                        "ticker": dossier.ticker,
                        "status": dossier.status.value,
                        "quality_flags": list(dossier.quality_flags),
                        "evidence_fingerprint": dossier.evidence_fingerprint,
                    }
                )
            except Exception as exc:
                dossier = self.queue.fail(
                    request,
                    error=f"{type(exc).__name__}: {exc}",
                    model=getattr(self.analyst.client, "model", "unknown"),
                )
                results.append(
                    {
                        "analysis_id": dossier.analysis_id,
                        "ticker": dossier.ticker,
                        "status": dossier.status.value,
                        "quality_flags": list(dossier.quality_flags),
                        "error": dossier.analysis.get("error") if dossier.analysis else None,
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
            "remaining_queue": len(self.queue.pending()),
            "results": results,
        }
        manifest_path = self.queue.manifests_dir / "latest.json"
        temp = manifest_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(manifest_path)
        return manifest
