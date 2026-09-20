from __future__ import annotations

from fastapi.testclient import TestClient

from b3_agent import server


def test_dashboard_orchestrate_uses_dashboard_workflow(monkeypatch) -> None:
    calls = []

    def fake_dashboard_workflow():
        calls.append("dashboard")

    def fake_orchestrator(task, ticker=None, context=None):
        from b3_agent.orchestration import OrchestratorResponse
        return OrchestratorResponse(
            status="COMPLETED",
            result={"dashboard_snapshot": {"portfolio_context": {"as_of": "2026-09-18"}, "options_transactions": []}},
        )

    monkeypatch.setattr(server, "configure_dashboard_workflow", fake_dashboard_workflow)
    monkeypatch.setattr(server, "b3_orchestrator", fake_orchestrator)
    server._configure_runtime.cache_clear()

    client = TestClient(server.app)
    response = client.post(
        "/orchestrate",
        json={
            "task": "Carregar portfolio",
            "context": {"client": "react-dashboard", "dashboard_view": "portfolio"},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    assert calls == ["dashboard"]
