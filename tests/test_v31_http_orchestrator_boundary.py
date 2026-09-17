from __future__ import annotations

from fastapi.testclient import TestClient

from b3_agent.orchestration.contracts import OrchestratorResponse
from b3_agent.orchestration import server


def test_health_is_transport_only():
    response = TestClient(server.app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_http_boundary_delegates_to_canonical_orchestrator(monkeypatch):
    calls: list[tuple[str, str | None, dict]] = []

    def fake_orchestrator(task: str, ticker: str | None = None, context: dict | None = None):
        calls.append((task, ticker, context or {}))
        return OrchestratorResponse(
            status="PASS",
            result={"answer": "structured result"},
            sources=("test-source",),
            audit=({"event": "test"},),
        )

    monkeypatch.setattr(server, "b3_orchestrator", fake_orchestrator)

    response = TestClient(server.app).post(
        "/v1/orchestrate",
        json={
            "task": "Analyze PETR4",
            "ticker": "petr4",
            "context": {"request_id": "test-1"},
        },
    )

    assert response.status_code == 200
    assert calls == [("Analyze PETR4", "petr4", {"request_id": "test-1"})]
    assert response.json() == {
        "status": "PASS",
        "result": {"answer": "structured result"},
        "sources": ["test-source"],
        "audit": [{"event": "test"}],
        "error": None,
    }


def test_http_boundary_rejects_empty_task():
    response = TestClient(server.app).post(
        "/v1/orchestrate",
        json={"task": "", "ticker": "PETR4"},
    )

    assert response.status_code == 422
