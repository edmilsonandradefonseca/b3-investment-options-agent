from __future__ import annotations

import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TextIO


DEFAULT_LOCK_PATH = "/var/lock/local-reasoning.lock"
FALLBACK_LOCK_PATH = "/tmp/local-reasoning.lock"


class LocalReasoningBusy(RuntimeError):
    """Raised when another project owns the shared local inference lock."""


@contextmanager
def local_reasoning_lock(
    *,
    path: str | Path | None = None,
    wait_seconds: float | None = None,
    poll_seconds: float = 0.1,
) -> Iterator[Path]:
    configured = Path(
        path
        or os.getenv("LOCAL_REASONING_LOCK_PATH")
        or DEFAULT_LOCK_PATH
    )
    wait = (
        float(os.getenv("LOCAL_REASONING_LOCK_WAIT_SECONDS", "5"))
        if wait_seconds is None
        else float(wait_seconds)
    )
    if wait < 0:
        raise ValueError("wait_seconds must be >= 0")

    handle, actual_path = _open_lock(configured)
    deadline = time.monotonic() + wait
    acquired = False
    try:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise LocalReasoningBusy(
                        f"local reasoning lock busy: {actual_path}"
                    ) from exc
                time.sleep(poll_seconds)
        yield actual_path
    finally:
        if acquired:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _open_lock(path: Path) -> tuple[TextIO, Path]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.open("a+", encoding="utf-8"), path
    except PermissionError:
        fallback = Path(FALLBACK_LOCK_PATH)
        return fallback.open("a+", encoding="utf-8"), fallback
