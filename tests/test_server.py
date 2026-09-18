from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from fastapi.testclient import TestClient

from b3_agent import server
from b3_agent.orchestration import OrchestratorResponse


client = TestClient(server.app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "b3-orchestrator-server"


def test_version_endpoint() -> None:
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {
        "service": "b3-orchestrator-server",
        "version": server.app.version,
    }


def test_orchestrate_delegates_to_logical_contract(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_configure() -> None:
        calls["configured"] = True

    def fake_orchestrator(*, task: str, ticker: str | None, context: dict) -> OrchestratorResponse:
        calls["request"] = {"task": task, "ticker": ticker, "context": context}
        return OrchestratorResponse(
            status="COMPLETED",
            result={"decision_proposal": {"action": "HOLD"}},
            sources=("obsidian/test.md",),
        )

    monkeypatch.setattr(server, "_configure_runtime", fake_configure)
    monkeypatch.setattr(server, "b3_orchestrator", fake_orchestrator)

    response = client.post(
        "/orchestrate",
        json={"task": "Analyze ITUB4", "ticker": "itub4", "context": {"foo": "bar"}},
    )

    assert response.status_code == 200
    assert calls["configured"] is True
    assert calls["request"] == {
        "task": "Analyze ITUB4",
        "ticker": "ITUB4",
        "context": {"foo": "bar"},
    }
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["result"]["decision_proposal"]["action"] == "HOLD"
    assert response.json()["sources"] == ["obsidian/test.md"]


def test_orchestrate_rejects_unknown_fields() -> None:
    response = client.post("/orchestrate", json={"task": "Analyze", "unknown": True})

    assert response.status_code == 422


def test_orchestrate_reports_runtime_configuration_failure(monkeypatch) -> None:
    def fail_configure() -> None:
        raise RuntimeError("B3_AGENT_OBSIDIAN_VAULT is not configured")

    monkeypatch.setattr(server, "_configure_runtime", fail_configure)

    response = client.post("/orchestrate", json={"task": "Analyze ITUB4"})

    assert response.status_code == 503
    assert "OBSIDIAN_VAULT" in response.json()["detail"]



def test_replace_validated_upload_preserves_excel_extension(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(server, "_import_dir", lambda: tmp_path)
    seen: dict[str, str] = {}

    def validator(path: Path) -> None:
        seen["suffix"] = path.suffix
        seen["content"] = path.read_bytes().decode("utf-8")

    upload = UploadFile(filename="portfolio.xlsx", file=BytesIO(b"excel-bytes"))
    result = server._replace_validated_upload(upload, "portfolio.xlsx", validator)

    assert seen == {"suffix": ".xlsx", "content": "excel-bytes"}
    assert result["status"] == "replaced"
    assert (tmp_path / "portfolio.xlsx").read_bytes() == b"excel-bytes"
