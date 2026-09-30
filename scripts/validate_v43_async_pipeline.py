#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from b3_agent.config import settings
from b3_agent.intelligence.local_evidence_analysis import (
    LocalAnalysisStatus,
    LocalEvidenceContextSelector,
    LocalEvidenceQueue,
)
from b3_agent.intelligence.official_sources import load_open_data_official_evidence
from b3_agent.intelligence.senior_context import SeniorEvidenceContextBuilder
from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob
from b3_agent.knowledge.evidence import Evidence


def _selected_material(ticker: str, year: int) -> tuple[Evidence, dict]:
    snapshot = load_open_data_official_evidence([ticker], year=year)
    evidences = [
        item
        for item in snapshot.by_ticker.get(ticker, ())
        if item.metadata.materiality == "MATERIAL"
    ]
    if not evidences:
        raise RuntimeError(f"no MATERIAL official Evidence for {ticker}/{year}")

    def timestamp(item: Evidence):
        return (
            item.metadata.published_at
            or item.metadata.reference_at
            or item.metadata.retrieved_at
        )

    selected = max(evidences, key=timestamp)
    return selected, snapshot.coverage


def _event(evidence: Evidence) -> dict:
    meta = evidence.metadata
    return {
        "evidence_type": "official_disclosure",
        "evidence_id": evidence.evidence_id,
        "ticker_refs": list(meta.ticker_refs),
        "issuer_ref": meta.issuer_ref,
        "cvm_code": meta.cvm_code,
        "published_at": meta.published_at.isoformat() if meta.published_at else None,
        "reference_at": meta.reference_at.isoformat() if meta.reference_at else None,
        "headline": evidence.title,
        "summary": evidence.content,
        "source_name": meta.source,
        "source_ref": evidence.source_url or evidence.evidence_id,
        "materiality": meta.materiality,
        "materiality_reason": meta.materiality_reason,
        "pit_status": meta.pit_status,
    }


def _root() -> Path:
    return settings.data_dir / "derived" / "v43_async_acceptance"


def enqueue_stage(ticker: str, year: int) -> int:
    started = time.monotonic()
    evidence, coverage = _selected_material(ticker, year)
    event = _event(evidence)
    queue = LocalEvidenceQueue(_root())
    result = queue.enqueue(ticker, [event])
    elapsed = time.monotonic() - started

    payload = {
        "status": "PASS",
        "stage": "enqueue",
        "ticker": ticker,
        "year": year,
        "elapsed_seconds": round(elapsed, 3),
        "deepseek_called": False,
        "official_sources_status": coverage.get("status"),
        "selected_evidence": {
            "evidence_id": evidence.evidence_id,
            "title": evidence.title,
            "source_ref": event["source_ref"],
            "materiality": event["materiality"],
            "materiality_reason": event["materiality_reason"],
            "pit_status": event["pit_status"],
        },
        "analysis_id": result.request.analysis_id,
        "evidence_fingerprint": result.request.evidence_fingerprint,
        "queue_status": result.queue_status,
        "pending_count": len(queue.pending()),
        "queue_root": str(_root()),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def worker_stage(ticker: str, year: int) -> int:
    evidence, coverage = _selected_material(ticker, year)
    event = _event(evidence)
    queue = LocalEvidenceQueue(_root())

    queued = queue.enqueue(ticker, [event])
    expected_id = queued.request.analysis_id

    started = time.monotonic()
    manifest = LocalEvidenceAnalystJob(queue=queue).run(limit=1)
    elapsed = time.monotonic() - started

    dossier = queue.latest(ticker)
    if dossier is None:
        raise RuntimeError("worker completed without a latest dossier")

    selector = LocalEvidenceContextSelector(queue)
    senior = SeniorEvidenceContextBuilder(selector).build(
        ticker=ticker,
        evidence_events=[event],
        as_of=datetime.now(timezone.utc),
    )

    if dossier.analysis_id != expected_id:
        raise RuntimeError(
            f"worker processed unexpected analysis_id {dossier.analysis_id}; "
            f"expected {expected_id}"
        )
    if dossier.status == LocalAnalysisStatus.FAILED:
        status = "FAIL"
        rc = 2
    elif dossier.status == LocalAnalysisStatus.READY:
        if senior.local_dossier_status != "READY" or senior.local_dossier is None:
            raise RuntimeError("READY dossier was not exposed to senior context")
        status = "PASS"
        rc = 0
    elif dossier.status == LocalAnalysisStatus.DEGRADED:
        if senior.local_dossier is not None:
            raise RuntimeError("DEGRADED dossier leaked into senior context")
        if senior.local_dossier_status != "OMITTED":
            raise RuntimeError("DEGRADED dossier was not explicitly omitted")
        status = "PASS_WITH_DEGRADED_LOCAL_DOSSIER"
        rc = 0
    else:
        status = "FAIL"
        rc = 2

    payload = {
        "status": status,
        "stage": "worker_and_senior_context",
        "ticker": ticker,
        "year": year,
        "official_sources_status": coverage.get("status"),
        "elapsed_seconds": round(elapsed, 3),
        "analysis_id": dossier.analysis_id,
        "evidence_fingerprint": dossier.evidence_fingerprint,
        "dossier_status": dossier.status.value,
        "quality_flags": list(dossier.quality_flags),
        "model": dossier.model,
        "eval_count": dossier.eval_count,
        "num_predict": dossier.num_predict,
        "input_chars": dossier.input_chars,
        "worker_manifest": manifest,
        "senior_context": {
            "canonical_evidence_count": len(senior.canonical_evidence),
            "local_dossier_status": senior.local_dossier_status,
            "local_dossier_reasons": list(senior.local_dossier_reasons),
            "local_dossier_included": senior.local_dossier is not None,
        },
        "acceptance": {
            "canonical_evidence_always_present": len(senior.canonical_evidence) == 1,
            "ready_is_reusable": (
                dossier.status != LocalAnalysisStatus.READY
                or senior.local_dossier is not None
            ),
            "degraded_is_omitted": (
                dossier.status != LocalAnalysisStatus.DEGRADED
                or senior.local_dossier is None
            ),
            "failed_is_not_accepted": dossier.status != LocalAnalysisStatus.FAILED,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return rc


def context_only_stage(ticker: str, year: int) -> int:
    evidence, _coverage = _selected_material(ticker, year)
    event = _event(evidence)
    queue = LocalEvidenceQueue(_root())
    senior = SeniorEvidenceContextBuilder(
        LocalEvidenceContextSelector(queue)
    ).build(
        ticker=ticker,
        evidence_events=[event],
        as_of=datetime.now(timezone.utc),
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "context_only",
                "ticker": ticker,
                "canonical_evidence_count": len(senior.canonical_evidence),
                "local_dossier_status": senior.local_dossier_status,
                "local_dossier_reasons": list(senior.local_dossier_reasons),
                "local_dossier_included": senior.local_dossier is not None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=("enqueue", "worker", "context"),
    )
    parser.add_argument("--ticker", default="PETR4")
    parser.add_argument("--year", type=int, default=datetime.now(timezone.utc).year)
    args = parser.parse_args()

    ticker = args.ticker.upper().strip()
    try:
        if args.stage == "enqueue":
            return enqueue_stage(ticker, args.year)
        if args.stage == "worker":
            return worker_stage(ticker, args.year)
        return context_only_stage(ticker, args.year)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "stage": args.stage,
                    "ticker": ticker,
                    "year": args.year,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
