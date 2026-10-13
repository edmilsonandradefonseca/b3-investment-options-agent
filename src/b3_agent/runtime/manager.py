from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from b3_agent.config import settings
from b3_agent.storage.sqlite import SQLiteStore


class RuntimeManager:
    """Infrastructure/lifecycle manager for the B3 runtime.

    It owns local runtime directories and the Orchestrator process lifecycle.
    Shared platform services (embedding, Qdrant and Neo4j) are observed only;
    they are never started/stopped by this manager.
    """

    def __init__(
        self,
        runtime_root: Path | None = None,
        project_root: Path | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        self.runtime_root = Path(
            runtime_root or os.getenv("B3_RUNTIME_ROOT", "/opt/b3-runtime")
        ).expanduser().resolve()
        self.project_root = Path(
            project_root or os.getenv("B3_AGENT_PROJECT_ROOT", settings.project_root)
        ).expanduser().resolve()
        self.host = host or os.getenv("B3_API_HOST", "127.0.0.1")
        self.port = int(port or os.getenv("B3_API_PORT", "8000"))
        self.health_timeout = float(os.getenv("B3_RUNTIME_HEALTH_TIMEOUT", "30"))

        self.data_dir = self.runtime_root / "data"
        self.imports_dir = self.data_dir / "imports"
        self.parquet_dir = self.data_dir / "parquet"
        self.logs_dir = self.runtime_root / "logs"
        self.backups_dir = self.runtime_root / "backups"
        self.runtime_pid_file = self.runtime_root / "runtime.pid"
        self.orchestrator_pid_file = self.runtime_root / "orchestrator.pid"

    @property
    def local_health_url(self) -> str:
        host = "127.0.0.1" if self.host in {"0.0.0.0", "::"} else self.host
        return f"http://{host}:{self.port}/health"

    def prepare_resources(self) -> dict[str, str]:
        for path in (
            self.runtime_root,
            self.data_dir,
            self.imports_dir,
            self.parquet_dir,
            self.logs_dir,
            self.backups_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        SQLiteStore(self.data_dir / "b3_agent.db").initialize()
        return self.resource_status()

    def resource_status(self) -> dict[str, str]:
        filesystem_ok = all(
            path.is_dir()
            for path in (
                self.runtime_root,
                self.data_dir,
                self.imports_dir,
                self.parquet_dir,
                self.logs_dir,
                self.backups_dir,
            )
        )
        sqlite_ok = (self.data_dir / "b3_agent.db").exists()
        return {
            "filesystem": "ok" if filesystem_ok else "missing",
            "sqlite": "ok" if sqlite_ok else "missing",
            "parquet": "ok" if self.parquet_dir.is_dir() else "missing",
        }

    @staticmethod
    def _read_pid(path: Path) -> int | None:
        try:
            return int(path.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError, OSError):
            return None

    @staticmethod
    def _process_running(pid: int | None) -> bool:
        if not pid or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError, OSError):
            return False

    @staticmethod
    def _http_probe(url: str, timeout: float = 2.0) -> bool:
        try:
            with urlopen(url, timeout=timeout) as response:
                return 200 <= response.status < 300
        except (URLError, TimeoutError, OSError):
            return False

    @staticmethod
    def _tcp_probe(uri: str, timeout: float = 2.0) -> bool:
        parsed = urlparse(uri)
        if not parsed.hostname or not parsed.port:
            return False
        try:
            with socket.create_connection((parsed.hostname, parsed.port), timeout=timeout):
                return True
        except OSError:
            return False

    def scheduler_status(self) -> dict[str, Any]:
        """Read B3 systemd timer dates without changing units or schedules."""
        try:
            result = subprocess.run(
                ["systemctl", "list-timers", "--all", "--no-pager", "--no-legend"],
                check=False,
                capture_output=True,
                text=True,
                timeout=4,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return {"state": "unavailable", "timers": []}

        if result.returncode != 0:
            return {"state": "unavailable", "timers": []}

        timers: list[dict[str, str | None]] = []
        for line in result.stdout.splitlines():
            fields = re.split(r"\s{2,}", line.strip())
            timer_unit = next(
                (field for field in fields if field.startswith("b3-") and field.endswith(".timer")),
                None,
            )
            if timer_unit is None:
                continue
            service_unit = next(
                (field for field in fields if field.startswith("b3-") and field.endswith(".service")),
                None,
            )
            timers.append(
                {
                    "unit": timer_unit,
                    "activates": service_unit,
                    "next": fields[0] if fields and fields[0] != "-" else None,
                    "last": fields[2] if len(fields) > 2 and fields[2] != "-" else None,
                }
            )
        return {"state": "ok", "timers": timers}

    def probe_health(self) -> bool:
        return self._http_probe(self.local_health_url)

    def shared_services_status(self) -> dict[str, dict[str, Any]]:
        embedding_url = os.getenv("B3_EMBEDDING_URL", "http://127.0.0.1:8093").rstrip("/")
        qdrant_url = os.getenv("B3_QDRANT_URL", "http://127.0.0.1:6333").rstrip("/")
        neo4j_uri = os.getenv("B3_NEO4J_URI", "bolt://127.0.0.1:7687")
        openclaw_url = (
            os.getenv("B3_OPENCLAW_GATEWAY_URL")
            or os.getenv("OPENCLAW_GATEWAY_URL")
            or "ws://127.0.0.1:18789"
        )

        return {
            "embedding": {
                "state": "ok" if self._http_probe(f"{embedding_url}/health") else "unavailable",
                "ownership": "shared_external",
                "endpoint": embedding_url,
            },
            "qdrant": {
                "state": "ok" if self._http_probe(f"{qdrant_url}/healthz") else "unavailable",
                "ownership": "shared_external",
                "endpoint": qdrant_url,
            },
            "neo4j": {
                "state": "ok" if self._tcp_probe(neo4j_uri) else "unavailable",
                "ownership": "shared_external",
                "endpoint": neo4j_uri,
            },
            "openclaw_gateway": {
                "state": "ok" if self._tcp_probe(openclaw_url) else "unavailable",
                "ownership": "shared_external",
                "endpoint": openclaw_url,
            },
        }

    def status(self, *, health_override: str | None = None) -> dict[str, Any]:
        runtime_pid = self._read_pid(self.runtime_pid_file)
        orchestrator_pid = self._read_pid(self.orchestrator_pid_file)
        runtime_running = self._process_running(runtime_pid)
        orchestrator_running = self._process_running(orchestrator_pid)

        if health_override is None:
            health = "ok" if self.probe_health() else "failed"
        else:
            health = health_override

        return {
            "runtime": "running" if runtime_running else "stopped",
            "runtime_root": str(self.runtime_root),
            "health": health,
            "api": {
                "host": self.host,
                "port": self.port,
                "local_health_url": self.local_health_url,
            },
            "resources": self.resource_status(),
            "services": self.shared_services_status(),
            "scheduler": self.scheduler_status(),
            "process": {
                "running": runtime_running and orchestrator_running,
                "runtime_pid": runtime_pid,
                "runtime_pid_running": runtime_running,
                "orchestrator_pid": orchestrator_pid,
                "orchestrator_pid_running": orchestrator_running,
            },
        }

    def doctor(self) -> dict[str, Any]:
        snapshot = self.status()
        checks = {
            "project_root": self.project_root.is_dir(),
            "python": Path(sys.executable).exists(),
            "runtime_root": self.runtime_root.is_dir(),
            "filesystem": snapshot["resources"]["filesystem"] == "ok",
            "sqlite": snapshot["resources"]["sqlite"] == "ok",
            "parquet": snapshot["resources"]["parquet"] == "ok",
            "orchestrator_health": snapshot["health"] == "ok",
            "embedding": snapshot["services"]["embedding"]["state"] == "ok",
            "qdrant": snapshot["services"]["qdrant"]["state"] == "ok",
            "neo4j": snapshot["services"]["neo4j"]["state"] == "ok",
        }
        return {
            "status": "ok" if all(checks.values()) else "attention",
            "checks": checks,
            "runtime": snapshot,
        }

    def _child_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["B3_AGENT_PROJECT_ROOT"] = str(self.project_root)
        env["B3_AGENT_DATA_DIR"] = str(self.data_dir)
        env["B3_AGENT_LOGS_DIR"] = str(self.logs_dir)
        return env

    def start_orchestrator(self) -> subprocess.Popen[bytes]:
        self.prepare_resources()
        existing = self._read_pid(self.orchestrator_pid_file)
        if self._process_running(existing):
            raise RuntimeError(f"orchestrator already running with pid {existing}")

        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "b3_agent.server:app",
                "--host",
                self.host,
                "--port",
                str(self.port),
            ],
            cwd=self.project_root,
            env=self._child_environment(),
        )
        self.orchestrator_pid_file.write_text(str(process.pid), encoding="utf-8")

        deadline = time.monotonic() + self.health_timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.orchestrator_pid_file.unlink(missing_ok=True)
                raise RuntimeError(
                    f"orchestrator exited before health check (code={process.returncode})"
                )
            if self.probe_health():
                return process
            time.sleep(0.25)

        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        self.orchestrator_pid_file.unlink(missing_ok=True)
        raise RuntimeError(
            f"orchestrator did not become healthy within {self.health_timeout:g}s"
        )

    def run_foreground(self) -> int:
        self.prepare_resources()
        self.runtime_pid_file.write_text(str(os.getpid()), encoding="utf-8")
        process: subprocess.Popen[bytes] | None = None
        stopping = False

        def stop_handler(_signum: int, _frame: Any) -> None:
            nonlocal stopping
            stopping = True
            if process is not None and process.poll() is None:
                process.terminate()

        previous_term = signal.signal(signal.SIGTERM, stop_handler)
        previous_int = signal.signal(signal.SIGINT, stop_handler)
        try:
            process = self.start_orchestrator()
            while process.poll() is None and not stopping:
                time.sleep(0.5)
            if process.poll() is None:
                process.terminate()
            try:
                return process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                return process.wait(timeout=5)
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            signal.signal(signal.SIGINT, previous_int)
            self.orchestrator_pid_file.unlink(missing_ok=True)
            self.runtime_pid_file.unlink(missing_ok=True)

    def format_status(self) -> str:
        s = self.status()
        services = s["services"]
        resources = s["resources"]
        process = s["process"]
        return "\n".join(
            [
                f"runtime {s['runtime']}",
                f"runtime_root {s['runtime_root']}",
                f"health {s['health']}",
                "resources "
                + "/".join(
                    f"{name}:{state}" for name, state in resources.items()
                ),
                "services "
                + "/".join(
                    f"{name}:{payload['state']}" for name, payload in services.items()
                ),
                f"api {s['api']['host']}:{s['api']['port']}",
                f"process running {str(process['running']).lower()}",
                f"runtime_pid {process['runtime_pid'] or '-'}",
                f"orchestrator_pid {process['orchestrator_pid'] or '-'}",
            ]
        )

    def format_doctor(self) -> str:
        report = self.doctor()
        lines = [f"doctor {report['status']}"]
        lines.extend(
            f"{name} {'ok' if passed else 'FAIL'}"
            for name, passed in report["checks"].items()
        )
        return "\n".join(lines)


def status_json(manager: RuntimeManager | None = None) -> str:
    return json.dumps((manager or RuntimeManager()).status(), indent=2, sort_keys=True)
