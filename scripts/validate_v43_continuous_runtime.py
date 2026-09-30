#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent import server
from b3_agent.config import settings
from b3_agent.intelligence.discovery_cursor import DiscoveryCursorStore
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.local_evidence_analysis import (
    LocalEvidenceContextSelector,
    LocalEvidenceQueue,
)
from b3_agent.intelligence.observability import local_intelligence_status
from b3_agent.intelligence.official_evidence import OfficialEvidenceBuilder
from b3_agent.intelligence.relevance_screen import LocalRelevanceQueue
from b3_agent.intelligence.senior_context import SeniorEvidenceContextBuilder
from b3_agent.jobs.continuous_intelligence import ContinuousIntelligenceJob
from b3_agent.jobs.cvm_open_data import CvmOpenDataBackfillJob
from b3_agent.jobs.cvm_reconciliation import CvmReconciliationJob
from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob
from b3_agent.jobs.local_relevance_screen import LocalRelevanceScreenJob
from b3_agent.llm.host_lock import local_reasoning_lock
from b3_agent.providers.cvm_rad import CvmRadDisclosureProvider


ACCEPTANCE_VERSION = "v43-continuous-runtime-1"


def _event(evidence):
    metadata = evidence.metadata
    return {
        "evidence_type": "official_disclosure",
        "evidence_id": evidence.evidence_id,
        "ticker_refs": list(metadata.ticker_refs),
        "issuer_ref": metadata.issuer_ref,
        "cvm_code": metadata.cvm_code,
        "published_at": (
            metadata.published_at.isoformat() if metadata.published_at else None
        ),
        "reference_at": (
            metadata.reference_at.isoformat() if metadata.reference_at else None
        ),
        "headline": evidence.title,
        "summary": evidence.content,
        "source_name": metadata.source,
        "source_ref": evidence.source_url or evidence.evidence_id,
        "materiality": metadata.materiality,
        "materiality_reason": metadata.materiality_reason,
        "pit_status": metadata.pit_status,
    }


def _select_live_examples(provider, builder, now):
    candidate = None
    material = None
    mapped = None
    queried = []
    for offset in range(5):
        day = now.date() - timedelta(days=offset)
        result = provider.query_ipe(day)
        queried.append(
            {
                "date": day.isoformat(),
                "documents": len(result.disclosures),
                "source_error_code": result.source_error_code,
            }
        )
        for disclosure in result.disclosures:
            evidence = builder.from_rad(disclosure)
            if not evidence.metadata.ticker_refs:
                continue
            mapped = mapped or evidence
            if evidence.metadata.materiality == "CANDIDATE" and candidate is None:
                candidate = evidence
            if evidence.metadata.materiality == "MATERIAL" and material is None:
                material = evidence
        if candidate is not None and material is not None:
            break
    if candidate is None:
        raise RuntimeError(
            "No mapped live CANDIDATE found in the last five days; "
            "continuous relevance runtime cannot be accepted."
        )
    return candidate, material, mapped, queried


def main() -> int:
    if not os.getenv("CVM_DM_USER") or not os.getenv("CVM_DM_PASS"):
        raise RuntimeError(
            "CVM Download Multiplo runtime credentials are not configured"
        )

    now = datetime.now(ZoneInfo(settings.timezone))
    acceptance_data = (
        settings.data_dir / "derived" / "v43_continuous_acceptance" / "data"
    )
    shutil.rmtree(acceptance_data.parent, ignore_errors=True)
    acceptance_data.mkdir(parents=True, exist_ok=True)

    registry = IssuerRegistry()
    provider = CvmRadDisclosureProvider()
    builder = OfficialEvidenceBuilder(registry=registry)
    candidate, material, mapped, prescan = _select_live_examples(
        provider,
        builder,
        now,
    )

    selected = []
    for evidence in (candidate, material, mapped):
        if evidence is None:
            continue
        for ticker in evidence.metadata.ticker_refs:
            if ticker not in selected:
                selected.append(ticker)
    if not selected:
        raise RuntimeError("live RAD examples did not resolve any ticker")

    cursor = DiscoveryCursorStore(
        acceptance_data / "structured" / "cvm_rad_discovery_cursor.json",
        overlap_minutes=24 * 60,
        initial_lookback_hours=5 * 24,
    )
    dossier_queue = LocalEvidenceQueue(
        acceptance_data / "derived" / "local_evidence_analyst"
    )
    relevance_queue = LocalRelevanceQueue(
        acceptance_data / "derived" / "local_relevance_screen"
    )
    continuous = ContinuousIntelligenceJob(
        provider=provider,
        registry=registry,
        cursor_store=cursor,
        dossier_queue=dossier_queue,
        relevance_queue=relevance_queue,
        root=acceptance_data / "derived" / "continuous_intelligence",
    )

    first = continuous.run(now=now, monitored_tickers=selected)
    evidence_files_after_first = len(
        list(
            (
                acceptance_data
                / "derived"
                / "continuous_intelligence"
                / "evidence"
            ).glob("*.json")
        )
    )
    if first["deepseek_called_inline"] is not False:
        raise RuntimeError("continuous discovery invoked DeepSeek inline")
    if first["metrics"]["new_evidence"] < 1:
        raise RuntimeError("continuous discovery persisted no canonical Evidence")
    if first["metrics"]["relevance_enqueued"] < 1:
        raise RuntimeError("mapped CANDIDATE did not reach relevance queue")

    first_cursor = cursor.load()
    if not first_cursor.last_successful_requested_at:
        raise RuntimeError("cursor did not advance after successful persistence")

    relevance_result = LocalRelevanceScreenJob(
        queue=relevance_queue,
        dossier_queue=dossier_queue,
        output_root=acceptance_data / "derived" / "local_relevance_screen",
    ).run(limit=1)
    if relevance_result["processed"] != 1:
        raise RuntimeError("relevance worker did not process one queued candidate")
    screen_row = relevance_result["results"][0]
    if screen_row["status"] not in {"READY", "DEGRADED", "DEFERRED"}:
        raise RuntimeError(
            "relevance screen was not safely contained: "
            f"{screen_row}"
        )
    if (
        screen_row["status"] != "READY"
        and screen_row.get("dossier_queue_status") != "NOT_PROMOTED"
    ):
        raise RuntimeError(
            "non-ready relevance output was incorrectly promoted: "
            f"{screen_row}"
        )

    second = continuous.run(
        now=now + timedelta(minutes=1),
        monitored_tickers=selected,
    )
    evidence_files_after_second = len(
        list(
            (
                acceptance_data
                / "derived"
                / "continuous_intelligence"
                / "evidence"
            ).glob("*.json")
        )
    )
    if second["metrics"]["duplicates"] < 1:
        raise RuntimeError("overlap poll did not exercise Evidence dedupe")
    if evidence_files_after_second < evidence_files_after_first:
        raise RuntimeError("append-only Evidence store lost records")

    lock_queue = LocalEvidenceQueue(
        acceptance_data / "derived" / "lock_acceptance_dossier"
    )
    lock_event = _event(material or candidate)
    lock_queue.enqueue(selected[0], [lock_event])
    acceptance_lock_path = acceptance_data / "shared-lock-acceptance.lock"
    old_wait = os.environ.get("LOCAL_REASONING_LOCK_WAIT_SECONDS")
    old_path = os.environ.get("LOCAL_REASONING_LOCK_PATH")
    os.environ["LOCAL_REASONING_LOCK_WAIT_SECONDS"] = "0"
    os.environ["LOCAL_REASONING_LOCK_PATH"] = str(acceptance_lock_path)
    try:
        with local_reasoning_lock(
            path=acceptance_lock_path,
            wait_seconds=0,
        ):
            lock_result = LocalEvidenceAnalystJob(
                queue=lock_queue,
                output_root=acceptance_data / "derived" / "lock_acceptance_dossier",
            ).run(limit=1)
    finally:
        if old_wait is None:
            os.environ.pop("LOCAL_REASONING_LOCK_WAIT_SECONDS", None)
        else:
            os.environ["LOCAL_REASONING_LOCK_WAIT_SECONDS"] = old_wait
        if old_path is None:
            os.environ.pop("LOCAL_REASONING_LOCK_PATH", None)
        else:
            os.environ["LOCAL_REASONING_LOCK_PATH"] = old_path

    if lock_result.get("deferred") != 1:
        raise RuntimeError(
            "shared local reasoning lock did not defer the B3 worker"
        )
    if lock_result.get("remaining_queue") != 1:
        raise RuntimeError("deferred local analysis was not requeued")

    senior = SeniorEvidenceContextBuilder(
        LocalEvidenceContextSelector(lock_queue)
    ).build(
        ticker=selected[0],
        evidence_events=[lock_event],
    )
    if not senior.canonical_evidence:
        raise RuntimeError("senior context lost canonical Evidence")
    if senior.local_dossier is not None:
        raise RuntimeError("pending/deferred dossier contaminated senior context")

    backfill = CvmOpenDataBackfillJob(
        registry=registry,
        output_dir=acceptance_data / "derived" / "cvm_open_data_ipe",
    )
    reconciliation = CvmReconciliationJob(
        registry=registry,
        backfill_job=backfill,
        continuous_root=(
            acceptance_data / "derived" / "continuous_intelligence"
        ),
        output_dir=acceptance_data / "derived" / "cvm_reconciliation",
    ).run(
        year=now.year,
        monitored_tickers=selected,
        as_of=now.date(),
    )
    if reconciliation["status"] != "PASS":
        raise RuntimeError("Open Data reconciliation failed")

    status = local_intelligence_status(acceptance_data)
    if status["status"] != "OK":
        raise RuntimeError("local observability status failed")

    client = TestClient(server.app)
    api_codes = {
        "status": client.get("/intelligence/local/status").status_code,
        "queue": client.get("/intelligence/local/queue").status_code,
        "manifest": client.get("/intelligence/local/manifest").status_code,
        "ticker": client.get(
            f"/intelligence/local/{selected[0]}"
        ).status_code,
    }
    if any(code != 200 for code in api_codes.values()):
        raise RuntimeError(
            "observability API validation failed: "
            f"ticker={selected[0]!r} codes={api_codes}"
        )

    result = {
        "V4_3_CONTINUOUS_ACCEPTANCE": "PASS",
        "acceptance_version": ACCEPTANCE_VERSION,
        "credentials": "PRESENT_NOT_PRINTED",
        "prescan": prescan,
        "selected_tickers": selected,
        "real_candidate": {
            "cvm_code": candidate.metadata.cvm_code,
            "tickers": list(candidate.metadata.ticker_refs),
            "materiality": candidate.metadata.materiality,
            "pit_status": candidate.metadata.pit_status,
        },
        "real_material_available": material is not None,
        "first_discovery": first["metrics"],
        "second_discovery": second["metrics"],
        "cursor_advanced": True,
        "overlap_dedupe": "PASS",
        "relevance_screen": {
            "status": screen_row["status"],
            "relevance": screen_row.get("relevance"),
            "quality_flags": screen_row.get("quality_flags"),
            "dossier_queue_status": screen_row.get("dossier_queue_status"),
            "error": screen_row.get("error"),
            "contained_nonblocking": screen_row["status"]
            in {"READY", "DEGRADED", "DEFERRED"},
        },
        "shared_lock": {
            "status": "PASS",
            "production_contract_path": (
                old_path or "/var/lock/local-reasoning.lock"
            ),
            "semantic_test_path": str(acceptance_lock_path),
            "worker_deferred": lock_result.get("deferred"),
            "remaining_queue": lock_result.get("remaining_queue"),
        },
        "senior_nonblocking": {
            "status": "PASS",
            "canonical_evidence_count": len(senior.canonical_evidence),
            "local_dossier_status": senior.local_dossier_status,
        },
        "reconciliation": reconciliation,
        "observability": {
            "status": status["status"],
            "queue_depths": status["queues"],
            "api_status_codes": api_codes,
        },
        "deepseek_inline": False,
        "previous_v43_degraded_dossier_gate": "ALREADY_PRODUCTION_VALIDATED",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
