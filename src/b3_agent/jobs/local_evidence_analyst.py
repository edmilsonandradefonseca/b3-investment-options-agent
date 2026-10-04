from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from time import monotonic

from b3_agent.config import settings
from b3_agent.llm.host_lock import LocalReasoningBusy, local_reasoning_lock
from b3_agent.intelligence.local_evidence_analysis import _atomic_json_write
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

    def run(self, *, limit: int = 5, deadline: float | None = None) -> dict[str, Any]:
        with local_reasoning_lock(path=self.queue.root / "worker.lock", wait_seconds=0):
            return self._run(limit=limit, deadline=deadline)

    def run_until_idle(self, *, limit: int = 5, max_batches: int = 20, max_seconds: float = 1800) -> dict[str, Any]:
        if min(limit, max_batches, max_seconds) <= 0:
            raise ValueError('Drain limits must be positive')
        deadline = monotonic() + max_seconds
        batches = []
        busy = False
        for _ in range(max_batches):
            if monotonic() >= deadline:
                break
            try:
                batch = self.run(limit=limit, deadline=deadline)
            except LocalReasoningBusy:
                busy = True
                break
            batches.append(batch)
            if batch['processed'] == 0 or batch['remaining_queue'] == 0:
                break
        manifest = {'as_of': datetime.now(timezone.utc).isoformat(),
                    'batches': len(batches), 'worker_busy': busy,
                    'remaining_queue': self.queue.outstanding_count(),
                    'results': [row for batch in batches for row in batch['results']]}
        for key in ('processed', 'ready', 'degraded', 'failed', 'deferred'):
            manifest[key] = sum(batch[key] for batch in batches)
        _atomic_json_write(self.queue.manifests_dir / 'latest.json', manifest)
        return manifest

    def _run(self, *, limit: int, deadline: float | None) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        requests = self.queue.pending(limit=limit)
        results: list[dict[str, Any]] = []

        for request in requests:
            if deadline is not None and monotonic() >= deadline:
                break
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
            except LocalReasoningBusy as exc:
                self.queue.defer(request, reason=str(exc))
                results.append(
                    {
                        "analysis_id": request.analysis_id,
                        "ticker": request.ticker,
                        "status": "DEFERRED",
                        "quality_flags": ["LOCAL_REASONING_BUSY"],
                        "error": str(exc),
                    }
                )
            except RuntimeError as exc:
                error = f"{type(exc).__name__}: {exc}"
                retry = self.queue.defer(request, reason=error, runtime_failure=True,
                                         model=getattr(self.analyst.client, "model", ""))
                results.append(
                    {
                        "analysis_id": request.analysis_id,
                        "ticker": request.ticker,
                        "status": "DEFERRED" if retry else "FAILED",
                        "quality_flags": ["LOCAL_MODEL_RUNTIME_FAILURE"] if retry else ["MODEL_FAILURE", "RETRY_EXHAUSTED"],
                        "error": error,
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
            "deferred": sum(item["status"] == "DEFERRED" for item in results),
            "remaining_queue": self.queue.outstanding_count(),
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
