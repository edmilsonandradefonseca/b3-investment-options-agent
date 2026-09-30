from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from b3_agent.intelligence.local_evidence_analysis import (
    LocalEvidenceQueue,
    evidence_fingerprint,
)
from b3_agent.llm.ollama_client import OllamaClient


RELEVANCE_POLICY_VERSION = "v4.3-local-relevance-1"
RELEVANCE_PROMPT_VERSION = "b3_local_relevance_screen_v1"

RELEVANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "relevance": {
            "type": "string",
            "enum": [
                "RELEVANT",
                "POSSIBLY_RELEVANT",
                "NOT_RELEVANT",
                "UNKNOWN",
            ],
        },
        "themes": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
        "senior_review_candidate": {"type": "boolean"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "relevance",
        "themes",
        "reason",
        "senior_review_candidate",
        "evidence_refs",
    ],
}


class RelevanceStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class RelevanceRequest:
    request_id: str
    ticker: str
    evidence_fingerprint: str
    evidence_events: tuple[dict[str, Any], ...]
    source_refs: tuple[str, ...]
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "ticker": self.ticker,
            "evidence_fingerprint": self.evidence_fingerprint,
            "evidence_events": list(self.evidence_events),
            "source_refs": list(self.source_refs),
            "created_at": self.created_at,
            "policy_version": RELEVANCE_POLICY_VERSION,
            "prompt_version": RELEVANCE_PROMPT_VERSION,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RelevanceRequest":
        return cls(
            request_id=str(value["request_id"]),
            ticker=str(value["ticker"]).upper().strip(),
            evidence_fingerprint=str(value["evidence_fingerprint"]),
            evidence_events=tuple(value.get("evidence_events") or ()),
            source_refs=tuple(str(item) for item in value.get("source_refs") or ()),
            created_at=str(value["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class RelevanceResult:
    request_id: str
    ticker: str
    evidence_fingerprint: str
    status: RelevanceStatus
    created_at: str
    model: str
    quality_flags: tuple[str, ...] = ()
    screen: dict[str, Any] | None = None
    eval_count: int | None = None
    num_predict: int | None = None
    total_duration_ns: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "ticker": self.ticker,
            "evidence_fingerprint": self.evidence_fingerprint,
            "status": self.status.value,
            "created_at": self.created_at,
            "model": self.model,
            "quality_flags": list(self.quality_flags),
            "screen": self.screen,
            "eval_count": self.eval_count,
            "num_predict": self.num_predict,
            "total_duration_ns": self.total_duration_ns,
        }


class LocalRelevanceQueue:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.queue_dir = self.root / "queue"
        self.runs_dir = self.root / "runs"
        self.manifests_dir = self.root / "manifests"
        for path in (self.queue_dir, self.runs_dir, self.manifests_dir):
            path.mkdir(parents=True, exist_ok=True)

    def enqueue(
        self,
        ticker: str,
        evidence_events: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    ) -> tuple[RelevanceRequest, str]:
        normalized = tuple(dict(item) for item in evidence_events)
        fingerprint = evidence_fingerprint(ticker, normalized)
        request_id = hashlib.sha256(
            (
                f"{ticker.upper().strip()}|{fingerprint}|"
                f"{RELEVANCE_PROMPT_VERSION}"
            ).encode("utf-8")
        ).hexdigest()
        refs = tuple(
            str(item.get("source_ref") or "").strip()
            for item in normalized
            if str(item.get("source_ref") or "").strip()
        )
        request = RelevanceRequest(
            request_id=request_id,
            ticker=ticker.upper().strip(),
            evidence_fingerprint=fingerprint,
            evidence_events=normalized,
            source_refs=refs,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        queued = self.queue_dir / f"{request_id}.json"
        run = self.runs_dir / f"{request_id}.json"
        if run.exists():
            return request, "ALREADY_PROCESSED"
        if queued.exists():
            return request, "ALREADY_QUEUED"
        _atomic_json_write(
            queued,
            {**request.as_dict(), "status": RelevanceStatus.PENDING.value},
        )
        return request, "ENQUEUED"

    def pending(self, *, limit: int | None = None) -> list[RelevanceRequest]:
        paths = sorted(self.queue_dir.glob("*.json"))
        if limit is not None:
            paths = paths[: max(0, int(limit))]
        return [
            RelevanceRequest.from_dict(
                json.loads(path.read_text(encoding="utf-8"))
            )
            for path in paths
        ]

    def mark_running(self, request: RelevanceRequest) -> None:
        _atomic_json_write(
            self.queue_dir / f"{request.request_id}.json",
            {
                **request.as_dict(),
                "status": RelevanceStatus.RUNNING.value,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def defer(self, request: RelevanceRequest, *, reason: str) -> None:
        _atomic_json_write(
            self.queue_dir / f"{request.request_id}.json",
            {
                **request.as_dict(),
                "status": RelevanceStatus.PENDING.value,
                "deferred_at": datetime.now(timezone.utc).isoformat(),
                "defer_reason": reason,
            },
        )

    def complete(self, result: RelevanceResult) -> None:
        _atomic_json_write(
            self.runs_dir / f"{result.request_id}.json",
            result.as_dict(),
        )
        (self.queue_dir / f"{result.request_id}.json").unlink(missing_ok=True)

    def fail(
        self,
        request: RelevanceRequest,
        *,
        error: str,
        model: str,
    ) -> RelevanceResult:
        result = RelevanceResult(
            request_id=request.request_id,
            ticker=request.ticker,
            evidence_fingerprint=request.evidence_fingerprint,
            status=RelevanceStatus.FAILED,
            created_at=datetime.now(timezone.utc).isoformat(),
            model=model,
            quality_flags=("MODEL_FAILURE",),
            screen={"error": error},
        )
        self.complete(result)
        return result


class LocalRelevanceAnalyst:
    def __init__(self, client: OllamaClient | None = None):
        self.client = client or OllamaClient(
            num_ctx=int(os.getenv("B3_RELEVANCE_NUM_CTX", "1024")),
            num_predict=int(os.getenv("B3_RELEVANCE_NUM_PREDICT", "192")),
            think=False,
            format_schema=RELEVANCE_SCHEMA,
        )

    def analyze(self, request: RelevanceRequest) -> RelevanceResult:
        result = self.client.ask(_prompt(request))
        flags: list[str] = []
        try:
            screen = json.loads(result.content)
            if not isinstance(screen, dict):
                raise ValueError("not object")
        except (json.JSONDecodeError, ValueError):
            screen = None
            flags.append("INVALID_JSON")

        if result.eval_count is not None and result.eval_count >= self.client.num_predict:
            flags.append("OUTPUT_LIMIT_REACHED")

        if screen is not None:
            allowed_relevance = {
                "RELEVANT",
                "POSSIBLY_RELEVANT",
                "NOT_RELEVANT",
                "UNKNOWN",
            }
            required_types = {
                "relevance": str,
                "themes": list,
                "reason": str,
                "senior_review_candidate": bool,
                "evidence_refs": list,
            }
            if (
                any(
                    key not in screen
                    or not isinstance(screen.get(key), expected)
                    for key, expected in required_types.items()
                )
                or screen.get("relevance") not in allowed_relevance
            ):
                flags.append("INVALID_SCHEMA")
            refs = screen.get("evidence_refs")
            if not isinstance(refs, list) or not set(
                str(item) for item in refs
            ).issubset(set(request.source_refs)):
                flags.append("UNKNOWN_EVIDENCE_REF")

        status = RelevanceStatus.READY if not flags else RelevanceStatus.DEGRADED
        return RelevanceResult(
            request_id=request.request_id,
            ticker=request.ticker,
            evidence_fingerprint=request.evidence_fingerprint,
            status=status,
            created_at=datetime.now(timezone.utc).isoformat(),
            model=result.model,
            quality_flags=tuple(dict.fromkeys(flags)),
            screen=screen,
            eval_count=result.eval_count,
            num_predict=self.client.num_predict,
            total_duration_ns=result.total_duration_ns,
        )


def should_promote_to_dossier(result: RelevanceResult) -> bool:
    if result.status != RelevanceStatus.READY or not result.screen:
        return False
    return result.screen.get("relevance") in {
        "RELEVANT",
        "POSSIBLY_RELEVANT",
    }


def promote_to_dossier(
    request: RelevanceRequest,
    result: RelevanceResult,
    dossier_queue: LocalEvidenceQueue,
) -> str:
    if not should_promote_to_dossier(result):
        return "NOT_PROMOTED"
    enqueue = dossier_queue.enqueue(request.ticker, request.evidence_events)
    return enqueue.queue_status


def _prompt(request: RelevanceRequest) -> str:
    return (
        "You are the B3 local relevance screen. Classify only the supplied "
        "canonical evidence. Do not recommend trades, invent prices, infer "
        "materiality, or override deterministic classifications. Return ONLY "
        "the JSON object required by the schema."
        f"\nTicker: {request.ticker}"
        "\nAllowed evidence refs: "
        + json.dumps(list(request.source_refs), ensure_ascii=False)
        + "\nEvidence: "
        + json.dumps(list(request.evidence_events), ensure_ascii=False)
    )


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temp.replace(path)
