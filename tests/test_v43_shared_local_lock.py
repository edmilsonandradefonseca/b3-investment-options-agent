from __future__ import annotations

import json

import pytest

from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.intelligence.relevance_screen import LocalRelevanceQueue
from b3_agent.llm.host_lock import LocalReasoningBusy, local_reasoning_lock


def _event():
    return {
        "evidence_type": "official_disclosure",
        "evidence_id": "E1",
        "source_ref": "https://cvm.test/e1",
        "headline": "Fato Relevante",
        "summary": "Evento",
        "materiality": "MATERIAL",
        "pit_status": "OBSERVED_LIVE",
    }


def test_shared_local_reasoning_lock_is_exclusive(tmp_path):
    path = tmp_path / "local-reasoning.lock"
    with local_reasoning_lock(path=path, wait_seconds=0):
        with pytest.raises(LocalReasoningBusy):
            with local_reasoning_lock(path=path, wait_seconds=0):
                pass

    with local_reasoning_lock(path=path, wait_seconds=0) as acquired:
        assert acquired == path


def test_dossier_queue_defer_returns_request_to_pending(tmp_path):
    queue = LocalEvidenceQueue(tmp_path / "dossier")
    request = queue.enqueue("PETR4", [_event()]).request
    queue.mark_running(request)
    queue.defer(request, reason="busy")

    pending = queue.pending()
    assert pending == []  # Stored as PENDING, but waits for the busy backoff.
    assert queue.outstanding_count() == 1
    payload = json.loads(
        (queue.queue_dir / f"{request.analysis_id}.json").read_text(encoding="utf-8")
    )
    assert payload["status"] == "PENDING"
    assert payload["defer_reason"] == "busy"


def test_relevance_queue_defer_returns_request_to_pending(tmp_path):
    queue = LocalRelevanceQueue(tmp_path / "relevance")
    request, status = queue.enqueue("PETR4", [_event()])
    assert status == "ENQUEUED"
    queue.mark_running(request)
    queue.defer(request, reason="busy")

    pending = queue.pending()
    assert len(pending) == 1
    payload = json.loads(
        (queue.queue_dir / f"{request.request_id}.json").read_text(encoding="utf-8")
    )
    assert payload["status"] == "PENDING"
    assert payload["defer_reason"] == "busy"
