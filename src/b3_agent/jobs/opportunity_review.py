from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4


class OpportunityReviewStore:
    """Durable latest-result and run-state store for long UC-03 reviews."""

    def __init__(self, data_dir: Path) -> None:
        self.root = Path(data_dir) / "derived" / "opportunities"
        self.status_path = self.root / "status.json"
        self.result_path = self.root / "latest.json"
        self.lock_path = self.root / "review.lock"

    def try_acquire(self):
        self.root.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return None
        return handle

    @staticmethod
    def release(handle) -> None:
        if handle is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def begin(self) -> dict[str, Any]:
        previous = self.status()
        state = {
            "status": "RUNNING",
            "run_id": str(uuid4()),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "last_successful_at": previous.get("last_successful_at"),
            "result_available": self.result_path.is_file(),
            "error": None,
        }
        self._write(self.status_path, state)
        return state

    def complete(self, response: Any, started: dict[str, Any]) -> dict[str, Any]:
        payload = (
            response.model_dump(mode="json")
            if hasattr(response, "model_dump")
            else json.loads(json.dumps(response, ensure_ascii=False, default=str))
        )
        generated_at = datetime.now(timezone.utc).isoformat()
        result = {
            "generated_at": generated_at,
            "run_id": started["run_id"],
            "response": payload,
        }
        self._write(self.result_path, result)
        state = {
            "status": "COMPLETED",
            "run_id": started["run_id"],
            "started_at": started["started_at"],
            "finished_at": generated_at,
            "last_successful_at": generated_at,
            "result_available": True,
            "error": None,
        }
        self._write(self.status_path, state)
        return state

    def fail(self, error: str, started: dict[str, Any]) -> dict[str, Any]:
        state = {
            "status": "FAILED",
            "run_id": started.get("run_id"),
            "started_at": started.get("started_at"),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "last_successful_at": self.status().get("last_successful_at"),
            "result_available": self.result_path.is_file(),
            "error": str(error)[:1000],
        }
        self._write(self.status_path, state)
        return state

    def status(self) -> dict[str, Any]:
        state = self._read(self.status_path) or {
            "status": "NOT_STARTED",
            "run_id": None,
            "started_at": None,
            "finished_at": None,
            "last_successful_at": None,
            "result_available": self.result_path.is_file(),
            "error": None,
        }
        if state.get("status") == "RUNNING":
            try:
                started_at = datetime.fromisoformat(str(state["started_at"]).replace("Z", "+00:00"))
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - started_at.astimezone(timezone.utc) > timedelta(hours=2):
                    state.update({
                        "status": "FAILED",
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                        "result_available": self.result_path.is_file(),
                        "error": "RUN_EXCEEDED_2H",
                    })
                    self._write(self.status_path, state)
            except (KeyError, TypeError, ValueError):
                state.update({
                    "status": "FAILED",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "result_available": self.result_path.is_file(),
                    "error": "INVALID_RUN_STATUS",
                })
                self._write(self.status_path, state)
        return state

    def latest(self) -> dict[str, Any]:
        return self._read(self.result_path) or {
            "status": "NOT_AVAILABLE",
            "generated_at": None,
            "response": None,
        }

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, ValueError):
            return None

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
