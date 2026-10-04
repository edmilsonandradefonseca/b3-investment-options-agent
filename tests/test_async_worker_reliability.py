import json
from datetime import datetime, timedelta, timezone

import pytest

from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue, LocalEvidenceAnalyst
from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob
from b3_agent.llm.host_lock import local_reasoning_lock, LocalReasoningBusy
from test_v43_local_evidence_analysis import FakeClient, RuntimeFailingClient, _events


def test_due_filter_does_not_let_backoff_hide_other_assets(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    a = queue.enqueue('ITUB4', _events()).request
    b = queue.enqueue('BBDC4', _events()).request
    queue.mark_running(a)
    queue.defer(a, reason='temporary', runtime_failure=True)
    assert [r.analysis_id for r in queue.pending(limit=1)] == [b.analysis_id]
    assert queue.outstanding_count() == 2


def test_running_lease_and_crash_recovery(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    request = queue.enqueue('ITUB4', _events()).request
    queue.mark_running(request)
    assert not queue.pending()
    path = queue.queue_dir / f'{request.analysis_id}.json'
    payload = json.loads(path.read_text())
    payload['started_at'] = (datetime.now(timezone.utc) - timedelta(minutes=21)).isoformat()
    path.write_text(json.dumps(payload))
    assert queue.pending()[0].analysis_id == request.analysis_id


def test_runtime_retries_stop_without_reenqueue_loop(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    request = queue.enqueue('ITUB4', _events()).request
    worker = LocalEvidenceAnalystJob(queue=queue, analyst=LocalEvidenceAnalyst(RuntimeFailingClient()))
    for attempt in range(3):
        result = worker.run(limit=1)
        if attempt < 2:
            assert result['deferred'] == 1
            path = queue.queue_dir / f'{request.analysis_id}.json'
            payload = json.loads(path.read_text())
            payload.pop('next_attempt_at')
            path.write_text(json.dumps(payload))
    assert result['failed'] == 1 and result['remaining_queue'] == 0
    assert 'RETRY_EXHAUSTED' in queue.latest('ITUB4').quality_flags
    assert queue.enqueue('ITUB4', _events()).queue_status == 'ALREADY_PROCESSED'


def test_worker_lock_prevents_duplicate_claims(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    queue.enqueue('ITUB4', _events())
    client = FakeClient()
    worker = LocalEvidenceAnalystJob(queue=queue, analyst=LocalEvidenceAnalyst(client))
    with local_reasoning_lock(path=queue.root / 'worker.lock', wait_seconds=0):
        with pytest.raises(LocalReasoningBusy):
            worker.run()
    assert client.calls == 0 and queue.outstanding_count() == 1


def test_budget_expiry_preserves_unprocessed_queue(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    queue.enqueue('ITUB4', _events())
    client = FakeClient()
    result = LocalEvidenceAnalystJob(queue=queue, analyst=LocalEvidenceAnalyst(client)).run(deadline=0)
    assert result['processed'] == 0 and result['remaining_queue'] == 1 and client.calls == 0


def test_drain_crosses_batches_and_keeps_aggregate_manifest(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    for ticker in ('ITUB4', 'BBDC4', 'PETR4', 'VALE3', 'WEGE3', 'RENT3'):
        queue.enqueue(ticker, _events())
    worker = LocalEvidenceAnalystJob(queue=queue, analyst=LocalEvidenceAnalyst(FakeClient()))
    partial = worker.run_until_idle(limit=2, max_batches=1)
    assert partial['processed'] == 2 and partial['remaining_queue'] == 4
    result = worker.run_until_idle(limit=2)
    assert result['processed'] == result['ready'] == 4
    assert result['batches'] == 2 and result['remaining_queue'] == 0
    assert json.loads((queue.manifests_dir / 'latest.json').read_text())['ready'] == 4
