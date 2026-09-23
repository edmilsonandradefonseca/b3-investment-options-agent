from __future__ import annotations

from pathlib import Path
from typing import Any


class RuntimeManager:
    """Owns the infrastructure lifecycle of the local B3 runtime.

    This layer deliberately does not contain investment logic, LangGraph
    orchestration, LLM reasoning, or domain calculations.
    """

    def __init__(self, runtime_root: Path) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve()
        self.pid_file = self.runtime_root / "runtime.pid"
        self._process: Any | None = None
        self._embedding_process: Any | None = None

    def _orchestrator_command(self) -> list[str]:
        return [
            str(Path(__file__).resolve().parents[3] / ".venv" / "bin" / "python"),
            "-m",
            "b3_agent",
        ]

    def start(self) -> dict[str, Any]:
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.ensure_resources()

        if self._process_running():
            return self.status()

        embedding_process = self._launch_embedding_service()
        self._embedding_process = embedding_process

        process = self._launch_orchestrator()
        self._process = process
        self.pid_file.write_text(str(process.pid))

        if not self._wait_for_embedding_health():
            self._terminate_process(embedding_process.pid)
            self._embedding_process = None
            self._terminate_process(process.pid)
            self._process = None
            self.pid_file.unlink(missing_ok=True)
            raise RuntimeError("Embedding service failed health check")

        if not self._wait_for_health():
            self._terminate_process(process.pid)
            self._process = None
            self._terminate_process(embedding_process.pid)
            self._embedding_process = None
            self.pid_file.unlink(missing_ok=True)
            raise RuntimeError("B3 Orchestrator failed health check")

        return self.status()

    def stop(self) -> dict[str, Any]:
        if self._embedding_process is not None:
            try:
                if self._embedding_process.poll() is None:
                    self._terminate_process(self._embedding_process.pid)
            except Exception:
                pass
            self._embedding_process = None

        if self.pid_file.is_file():
            try:
                pid = int(self.pid_file.read_text().strip())
            except (OSError, ValueError):
                pid = None

            if pid is not None and pid > 0:
                self._terminate_process(pid)

            self._process = None
            self.pid_file.unlink(missing_ok=True)

        return self.status()

    def _launch_embedding_service(self) -> Any:
        import subprocess

        return subprocess.Popen(
            [
                "/opt/joao-runtime/embeddings/.venv/bin/uvicorn",
                "embedding_api:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8093",
            ],
            cwd="/opt/joao-runtime/embeddings",
            env=self._environment(),
        )

    def _launch_orchestrator(self) -> Any:
        import subprocess

        return subprocess.Popen(
            self._orchestrator_command(),
            cwd=str(Path(__file__).resolve().parents[3]),
            env=self._environment(),
        )

    def _terminate_process(self, pid: int) -> None:
        import os
        import signal

        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def _environment(self) -> dict[str, str]:
        import os

        environment = os.environ.copy()
        environment["B3_AGENT_DATA_DIR"] = str(self.runtime_root / "data")
        return environment

    def restart(self) -> dict[str, Any]:
        self.stop()
        return self.start()

    def status(self) -> dict[str, Any]:
        running = self._process_running()

        return {
            "runtime": "running" if running else "stopped",
            "runtime_root": str(self.runtime_root),
            "health": "ok" if running else "unknown",
            "resources": self.resource_status(),
            "services": self.service_status(),
            "process": {
                "running": running,
                "pid_file": str(self.pid_file),
            },
        }

    def ensure_resources(self) -> dict[str, str]:
        data_dir = self.runtime_root / "data"

        directories = [
            data_dir,
            data_dir / "imports",
            data_dir / "parquet",
            self.runtime_root / "logs",
            self.runtime_root / "backups",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        from b3_agent.storage.sqlite import SQLiteStore

        database = data_dir / "b3_agent.db"
        SQLiteStore(database).initialize()

        return self.resource_status()


    def resource_status(self) -> dict[str, str]:
        data_dir = self.runtime_root / "data"
        parquet_dir = data_dir / "parquet"
        database = data_dir / "b3_agent.db"

        filesystem_ok = all(
            directory.is_dir()
            for directory in (
                data_dir,
                data_dir / "imports",
                parquet_dir,
                self.runtime_root / "logs",
                self.runtime_root / "backups",
            )
        )

        sqlite_ok = database.is_file()

        parquet_ok = parquet_dir.is_dir()

        return {
            "filesystem": "ok" if filesystem_ok else "error",
            "sqlite": "ok" if sqlite_ok else "error",
            "parquet": "ok" if parquet_ok else "error",
        }


    def service_status(self) -> dict[str, str]:
        return {
            "qdrant": "running" if self._tcp_service_available("127.0.0.1", 6333) else "stopped",
            "neo4j": "running" if self._tcp_service_available("127.0.0.1", 7687) else "stopped",
            "embedding": "running" if self._embedding_service_available() else "stopped",
        }

    def _tcp_service_available(self, host: str, port: int) -> bool:
        import socket

        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            return False


    def doctor(self) -> dict[str, Any]:
        resources = self.resource_status()
        services = self.service_status()

        return {
            **resources,
            "services": services,
            "runtime_root": str(self.runtime_root),
        }


    def _process_running(self) -> bool:
        if self._process is not None:
            try:
                if self._process.poll() is None:
                    return True
            except Exception:
                pass

        if not self.pid_file.is_file():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
        except (OSError, ValueError):
            return False

        if pid <= 0:
            return False

        try:
            import os
            os.kill(pid, 0)
        except OSError:
            return False

        return True

    def health(self) -> dict[str, Any]:
        try:
            available = self.runtime_root.exists() and self.runtime_root.is_dir()
        except OSError:
            available = False

        return {
            "status": "ok" if available else "error",
            "runtime_root": str(self.runtime_root),
        }

    def _embedding_service_available(self) -> bool:
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:8093/health",
                timeout=1.0,
            ) as response:
                return response.status == 200
        except (OSError, urllib.error.URLError):
            return False

    def _wait_for_embedding_health(self) -> bool:
        import time

        deadline = time.monotonic() + 30.0

        while time.monotonic() < deadline:
            if self._embedding_service_available():
                return True
            time.sleep(0.25)

        return False

    def _wait_for_health(self) -> bool:
        import time
        import urllib.error
        import urllib.request

        url = "http://127.0.0.1:8000/health"
        deadline = time.monotonic() + 30.0

        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1.0) as response:
                    if response.status != 200:
                        time.sleep(0.25)
                        continue

                    import json
                    payload = json.loads(response.read().decode("utf-8"))

                    if payload.get("status") == "ok":
                        return True
            except (OSError, urllib.error.URLError, ValueError):
                pass

            time.sleep(0.25)

        return False
