from b3_agent.jobs.opportunity_review import OpportunityReviewStore


class Response:
    def __init__(self, value):
        self.value = value

    def model_dump(self, *, mode):
        assert mode == "json"
        return self.value


def test_review_store_persists_result_and_state(tmp_path):
    store = OpportunityReviewStore(tmp_path)
    started = store.begin()

    assert store.status()["status"] == "RUNNING"
    assert store.latest()["response"] is None

    state = store.complete(Response({"status": "COMPLETED", "result": {"derived_synthesis_status": "COMPLETED"}}), started)

    assert state["status"] == "COMPLETED"
    assert store.status()["last_successful_at"] == state["finished_at"]
    assert store.latest()["response"]["result"]["derived_synthesis_status"] == "COMPLETED"


def test_failed_refresh_preserves_last_successful_result(tmp_path):
    store = OpportunityReviewStore(tmp_path)
    first = store.begin()
    store.complete(Response({"status": "COMPLETED", "result": {"summary": "valid"}}), first)
    previous = store.latest()

    second = store.begin()
    failed = store.fail("provider unavailable", second)

    assert failed["status"] == "FAILED"
    assert store.status()["result_available"] is True
    assert store.latest() == previous


def test_review_lock_prevents_concurrent_runs_across_processes(tmp_path):
    store = OpportunityReviewStore(tmp_path)
    first = store.try_acquire()
    assert first is not None
    try:
        assert store.try_acquire() is None
    finally:
        store.release(first)

    second = store.try_acquire()
    assert second is not None
    store.release(second)
