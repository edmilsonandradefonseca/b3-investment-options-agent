from __future__ import annotations

from pathlib import Path

from b3_agent.runtime.manager import RuntimeManager


def test_prepare_resources_creates_runtime_contract(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path / "runtime", project_root=tmp_path)

    resources = manager.prepare_resources()

    assert resources == {
        "filesystem": "ok",
        "sqlite": "ok",
        "parquet": "ok",
    }
    assert manager.imports_dir.is_dir()
    assert manager.parquet_dir.is_dir()
    assert manager.logs_dir.is_dir()
    assert manager.backups_dir.is_dir()
    assert (manager.data_dir / "b3_agent.db").exists()


def test_status_preserves_runtime_contract(monkeypatch, tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path / "runtime", project_root=tmp_path)
    manager.prepare_resources()
    manager.runtime_pid_file.write_text("123", encoding="utf-8")
    manager.orchestrator_pid_file.write_text("456", encoding="utf-8")

    monkeypatch.setattr(manager, "_process_running", lambda pid: pid in {123, 456})
    monkeypatch.setattr(
        manager,
        "shared_services_status",
        lambda: {
            "embedding": {"state": "ok", "ownership": "shared_external"},
            "qdrant": {"state": "ok", "ownership": "shared_external"},
            "neo4j": {"state": "ok", "ownership": "shared_external"},
        },
    )

    status = manager.status(health_override="ok")

    assert status["runtime"] == "running"
    assert status["runtime_root"] == str(manager.runtime_root)
    assert status["health"] == "ok"
    assert status["resources"]["filesystem"] == "ok"
    assert status["resources"]["sqlite"] == "ok"
    assert status["resources"]["parquet"] == "ok"
    assert status["process"]["running"] is True
    assert status["process"]["runtime_pid"] == 123
    assert status["process"]["orchestrator_pid"] == 456
    assert status["services"]["qdrant"]["ownership"] == "shared_external"


def test_local_health_uses_loopback_when_bound_all_interfaces(tmp_path: Path) -> None:
    manager = RuntimeManager(
        runtime_root=tmp_path / "runtime",
        project_root=tmp_path,
        host="0.0.0.0",
        port=8000,
    )

    assert manager.local_health_url == "http://127.0.0.1:8000/health"
