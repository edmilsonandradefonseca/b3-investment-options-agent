from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


CURSOR_VERSION = "v4.3-cvm-rad-cursor-1"


@dataclass(frozen=True, slots=True)
class DiscoveryCursorState:
    source: str = "CVM_RAD"
    version: str = CURSOR_VERSION
    last_successful_requested_at: str | None = None
    last_successful_retrieval_at: str | None = None
    last_source_error: str | None = None
    overlap_minutes: int = 30
    recent_provider_ids: tuple[str, ...] = ()
    processed_evidence_keys: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "version": self.version,
            "last_successful_requested_at": self.last_successful_requested_at,
            "last_successful_retrieval_at": self.last_successful_retrieval_at,
            "last_source_error": self.last_source_error,
            "overlap_minutes": self.overlap_minutes,
            "recent_provider_ids": list(self.recent_provider_ids),
            "processed_evidence_keys": list(self.processed_evidence_keys),
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "DiscoveryCursorState":
        return cls(
            source=str(value.get("source") or "CVM_RAD"),
            version=str(value.get("version") or CURSOR_VERSION),
            last_successful_requested_at=(
                str(value["last_successful_requested_at"])
                if value.get("last_successful_requested_at")
                else None
            ),
            last_successful_retrieval_at=(
                str(value["last_successful_retrieval_at"])
                if value.get("last_successful_retrieval_at")
                else None
            ),
            last_source_error=(
                str(value["last_source_error"])
                if value.get("last_source_error")
                else None
            ),
            overlap_minutes=int(value.get("overlap_minutes") or 30),
            recent_provider_ids=tuple(
                str(item) for item in value.get("recent_provider_ids") or ()
            ),
            processed_evidence_keys=tuple(
                str(item) for item in value.get("processed_evidence_keys") or ()
            ),
        )


class DiscoveryCursorStore:
    """Restart-safe cursor. Cursor advancement happens only after persistence."""

    def __init__(
        self,
        path: str | Path,
        *,
        overlap_minutes: int = 30,
        initial_lookback_hours: int = 24,
        history_limit: int = 5000,
    ) -> None:
        if overlap_minutes < 0:
            raise ValueError("overlap_minutes must be >= 0")
        if initial_lookback_hours < 1:
            raise ValueError("initial_lookback_hours must be >= 1")
        if history_limit < 100:
            raise ValueError("history_limit must be >= 100")
        self.path = Path(path)
        self.overlap_minutes = int(overlap_minutes)
        self.initial_lookback_hours = int(initial_lookback_hours)
        self.history_limit = int(history_limit)

    def load(self) -> DiscoveryCursorState:
        if not self.path.exists():
            return DiscoveryCursorState(overlap_minutes=self.overlap_minutes)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        state = DiscoveryCursorState.from_dict(payload)
        return DiscoveryCursorState(
            source=state.source,
            version=state.version,
            last_successful_requested_at=state.last_successful_requested_at,
            last_successful_retrieval_at=state.last_successful_retrieval_at,
            last_source_error=state.last_source_error,
            overlap_minutes=self.overlap_minutes,
            recent_provider_ids=state.recent_provider_ids,
            processed_evidence_keys=state.processed_evidence_keys,
        )

    def query_window(
        self,
        *,
        now: datetime,
        state: DiscoveryCursorState | None = None,
    ) -> tuple[datetime, datetime]:
        _require_aware(now)
        current = state or self.load()
        if current.last_successful_requested_at:
            previous = _parse_timestamp(current.last_successful_requested_at)
            start = previous - timedelta(minutes=self.overlap_minutes)
        else:
            start = now - timedelta(hours=self.initial_lookback_hours)
        return start, now

    def commit_success(
        self,
        *,
        requested_through: datetime,
        retrieval_at: datetime,
        provider_ids: Iterable[str],
        processed_evidence_keys: Iterable[str],
        previous: DiscoveryCursorState | None = None,
    ) -> DiscoveryCursorState:
        _require_aware(requested_through)
        _require_aware(retrieval_at)
        prior = previous or self.load()
        state = DiscoveryCursorState(
            source=prior.source,
            version=CURSOR_VERSION,
            last_successful_requested_at=requested_through.isoformat(),
            last_successful_retrieval_at=retrieval_at.isoformat(),
            last_source_error=None,
            overlap_minutes=self.overlap_minutes,
            recent_provider_ids=_merge_tail(
                prior.recent_provider_ids,
                provider_ids,
                self.history_limit,
            ),
            processed_evidence_keys=_merge_tail(
                prior.processed_evidence_keys,
                processed_evidence_keys,
                self.history_limit,
            ),
        )
        self._write(state)
        return state

    def record_error(
        self,
        error: str,
        *,
        previous: DiscoveryCursorState | None = None,
    ) -> DiscoveryCursorState:
        prior = previous or self.load()
        state = DiscoveryCursorState(
            source=prior.source,
            version=CURSOR_VERSION,
            last_successful_requested_at=prior.last_successful_requested_at,
            last_successful_retrieval_at=prior.last_successful_retrieval_at,
            last_source_error=error,
            overlap_minutes=self.overlap_minutes,
            recent_provider_ids=prior.recent_provider_ids,
            processed_evidence_keys=prior.processed_evidence_keys,
        )
        self._write(state)
        return state

    def _write(self, state: DiscoveryCursorState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(
            json.dumps(state.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")


def _merge_tail(
    previous: Iterable[str],
    new_values: Iterable[str],
    limit: int,
) -> tuple[str, ...]:
    ordered = dict.fromkeys(
        str(item).strip()
        for item in (*tuple(previous), *tuple(new_values))
        if str(item).strip()
    )
    return tuple(ordered)[-limit:]
