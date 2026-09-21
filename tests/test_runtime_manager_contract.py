from pathlib import Path

from b3_agent.runtime.manager import RuntimeManager


def test_runtime_manager_exposes_lifecycle_operations(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    assert callable(manager.start)
    assert callable(manager.stop)
    assert callable(manager.restart)
    assert callable(manager.status)
    assert callable(manager.health)


def test_runtime_manager_status_starts_stopped(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    status = manager.status()

    assert status["runtime"] == "stopped"


def test_runtime_manager_health_reports_runtime_root(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    health = manager.health()

    assert health["status"] in {"ok", "error"}
    assert health["runtime_root"] == str(tmp_path)


def test_runtime_manager_status_contains_process_state(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    status = manager.status()

    assert "process" in status
    assert status["process"]["running"] is False


def test_runtime_manager_exposes_pid_file_path(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    assert manager.pid_file == tmp_path / "runtime.pid"


def test_runtime_manager_builds_orchestrator_command(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    command = manager._orchestrator_command()

    assert command[-1] == "b3_agent"
    assert "-m" in command
    assert "uvicorn" not in command


def test_runtime_manager_start_creates_pid_file(tmp_path: Path, monkeypatch) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    class FakeProcess:
        pid = 4242

        def poll(self):
            return None

    monkeypatch.setattr(manager, "_launch_orchestrator", lambda: FakeProcess())
    monkeypatch.setattr(manager, "_wait_for_health", lambda: True)

    status = manager.start()

    assert manager.pid_file.exists()
    assert manager.pid_file.read_text() == "4242"
    assert status["runtime"] == "running"
    assert status["process"]["running"] is True


def test_runtime_manager_stop_removes_pid_file(tmp_path: Path, monkeypatch) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)
    manager.pid_file.write_text("4242")

    monkeypatch.setattr(manager, "_terminate_process", lambda pid: None)

    status = manager.stop()

    assert not manager.pid_file.exists()
    assert status["runtime"] == "stopped"
    assert status["process"]["running"] is False


def test_runtime_manager_start_requires_health_check(tmp_path: Path, monkeypatch) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    class FakeProcess:
        pid = 4242

        def poll(self):
            return None

    monkeypatch.setattr(manager, "_launch_orchestrator", lambda: FakeProcess())
    monkeypatch.setattr(manager, "_wait_for_health", lambda: True)

    status = manager.start()

    assert status["runtime"] == "running"
    assert status["health"] == "ok"


def test_runtime_manager_start_fails_when_health_check_fails(
    tmp_path: Path, monkeypatch
) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    class FakeProcess:
        pid = 4242

        def poll(self):
            return None

    terminated = []

    monkeypatch.setattr(manager, "_launch_orchestrator", lambda: FakeProcess())
    monkeypatch.setattr(manager, "_wait_for_health", lambda: False)
    monkeypatch.setattr(
        manager,
        "_terminate_process",
        lambda pid: terminated.append(pid),
    )

    try:
        manager.start()
    except RuntimeError:
        pass
    else:
        raise AssertionError("start() must fail when health check fails")

    assert terminated == [4242]
    assert not manager.pid_file.exists()


def test_runtime_manager_ensures_runtime_directories(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    resources = manager.ensure_resources()

    assert resources["filesystem"] == "ok"
    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "data" / "imports").is_dir()
    assert (tmp_path / "data" / "parquet").is_dir()
    assert (tmp_path / "logs").is_dir()
    assert (tmp_path / "backups").is_dir()


def test_runtime_manager_initializes_sqlite(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    resources = manager.ensure_resources()

    assert resources["sqlite"] == "ok"
    database = tmp_path / "data" / "b3_agent.db"
    assert database.exists()


def test_runtime_manager_reports_parquet_readiness(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    resources = manager.ensure_resources()

    assert resources["parquet"] == "ok"
    assert (tmp_path / "data" / "parquet").is_dir()


def test_runtime_manager_status_reports_resources(tmp_path: Path) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    manager.ensure_resources()
    status = manager.status()

    assert status["resources"]["filesystem"] == "ok"
    assert status["resources"]["sqlite"] == "ok"
    assert status["resources"]["parquet"] == "ok"


def test_runtime_manager_reports_optional_services_as_disabled(
    tmp_path: Path,
) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    services = manager.service_status()

    assert services["qdrant"] == "disabled"
    assert services["neo4j"] == "disabled"


def test_runtime_manager_status_includes_optional_services(
    tmp_path: Path,
) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    status = manager.status()

    assert "services" in status
    assert status["services"]["qdrant"] == "disabled"
    assert status["services"]["neo4j"] == "disabled"


def test_runtime_manager_doctor_reports_runtime_dependencies(
    tmp_path: Path,
) -> None:
    manager = RuntimeManager(runtime_root=tmp_path)

    result = manager.doctor()

    assert result["filesystem"] in ("ok", "error")
    assert result["sqlite"] in ("ok", "error")
    assert result["parquet"] in ("ok", "error")
    assert result["services"]["qdrant"] == "disabled"
    assert result["services"]["neo4j"] == "disabled"
