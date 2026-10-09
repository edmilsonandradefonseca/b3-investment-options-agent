from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from b3_agent.llm.ollama_client import OllamaClient


POLICY_VERSION = "v4.3-local-evidence-1"
PROMPT_VERSION = "b3_local_evidence_analyst_v7"

LOCAL_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "maxLength": 400},
        "risks": {"type": "array", "maxItems": 2, "items": {"type": "string", "maxLength": 200}},
        "catalysts": {"type": "array", "maxItems": 2, "items": {"type": "string", "maxLength": 200}},
        "contradictions": {"type": "array", "maxItems": 2, "items": {"type": "string", "maxLength": 200}},
        "questions_for_senior_review": {
            "type": "array",
            "maxItems": 2,
            "items": {"type": "string", "maxLength": 200},
        },
        "escalation_recommended": {"type": "boolean"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "risks",
        "catalysts",
        "contradictions",
        "questions_for_senior_review",
        "escalation_recommended",
        "evidence_refs",
    ],
}


class LocalAnalysisStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class LocalEvidenceAnalysisRequest:
    analysis_id: str
    ticker: str
    evidence_fingerprint: str
    evidence_events: tuple[dict[str, Any], ...]
    source_refs: tuple[str, ...]
    created_at: str
    policy_version: str = POLICY_VERSION
    prompt_version: str = PROMPT_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "ticker": self.ticker,
            "evidence_fingerprint": self.evidence_fingerprint,
            "evidence_events": list(self.evidence_events),
            "source_refs": list(self.source_refs),
            "created_at": self.created_at,
            "policy_version": self.policy_version,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LocalEvidenceAnalysisRequest":
        return cls(
            analysis_id=str(value["analysis_id"]),
            ticker=str(value["ticker"]).upper().strip(),
            evidence_fingerprint=str(value["evidence_fingerprint"]),
            evidence_events=tuple(value.get("evidence_events") or ()),
            source_refs=tuple(str(item) for item in value.get("source_refs") or ()),
            created_at=str(value["created_at"]),
            policy_version=str(value.get("policy_version") or POLICY_VERSION),
            prompt_version=str(value.get("prompt_version") or PROMPT_VERSION),
        )


@dataclass(frozen=True, slots=True)
class LocalEvidenceDossier:
    analysis_id: str
    ticker: str
    evidence_fingerprint: str
    evidence_refs: tuple[str, ...]
    created_at: str
    model: str
    prompt_version: str
    status: LocalAnalysisStatus
    quality_flags: tuple[str, ...] = ()
    analysis: dict[str, Any] | None = None
    raw_analysis: str | None = None
    thinking_chars: int = 0
    input_chars: int = 0
    eval_count: int | None = None
    num_predict: int | None = None
    total_duration_ns: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "ticker": self.ticker,
            "evidence_fingerprint": self.evidence_fingerprint,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "status": self.status.value,
            "quality_flags": list(self.quality_flags),
            "analysis": self.analysis,
            "raw_analysis": self.raw_analysis,
            "thinking_chars": self.thinking_chars,
            "input_chars": self.input_chars,
            "eval_count": self.eval_count,
            "num_predict": self.num_predict,
            "total_duration_ns": self.total_duration_ns,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LocalEvidenceDossier":
        return cls(
            analysis_id=str(value["analysis_id"]),
            ticker=str(value["ticker"]).upper().strip(),
            evidence_fingerprint=str(value["evidence_fingerprint"]),
            evidence_refs=tuple(str(item) for item in value.get("evidence_refs") or ()),
            created_at=str(value["created_at"]),
            model=str(value.get("model") or ""),
            prompt_version=str(value.get("prompt_version") or PROMPT_VERSION),
            status=LocalAnalysisStatus(str(value["status"])),
            quality_flags=tuple(str(item) for item in value.get("quality_flags") or ()),
            analysis=value.get("analysis") if isinstance(value.get("analysis"), dict) else None,
            raw_analysis=(
                str(value["raw_analysis"])
                if value.get("raw_analysis") is not None
                else None
            ),
            thinking_chars=int(value.get("thinking_chars") or 0),
            input_chars=int(value.get("input_chars") or 0),
            eval_count=(
                int(value["eval_count"])
                if value.get("eval_count") is not None
                else None
            ),
            num_predict=(
                int(value["num_predict"])
                if value.get("num_predict") is not None
                else None
            ),
            total_duration_ns=(
                int(value["total_duration_ns"])
                if value.get("total_duration_ns") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class QueueEnqueueResult:
    request: LocalEvidenceAnalysisRequest
    queue_status: str


def evidence_fingerprint(
    ticker: str,
    evidence_events: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    policy_version: str = POLICY_VERSION,
) -> str:
    stable = {
        "ticker": ticker.upper().strip(),
        "policy_version": policy_version,
        "events": sorted(
            (_stable_event(event) for event in evidence_events),
            key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False),
        ),
    }
    payload = json.dumps(
        stable,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _stable_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_type": event.get("evidence_type"),
        "evidence_id": event.get("evidence_id"),
        "source_ref": event.get("source_ref"),
        "published_at": event.get("published_at"),
        "reference_at": event.get("reference_at"),
        "headline": event.get("headline"),
        "summary": event.get("summary"),
        "materiality": event.get("materiality"),
        "materiality_reason": event.get("materiality_reason"),
        "pit_status": event.get("pit_status"),
    }


def build_request(
    ticker: str,
    evidence_events: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> LocalEvidenceAnalysisRequest:
    normalized = tuple(dict(item) for item in evidence_events)
    fingerprint = evidence_fingerprint(ticker, normalized)
    analysis_id = hashlib.sha256(
        f"{ticker.upper().strip()}|{fingerprint}|{PROMPT_VERSION}".encode("utf-8")
    ).hexdigest()
    refs = tuple(
        str(item.get("source_ref") or "").strip()
        for item in normalized
        if str(item.get("source_ref") or "").strip()
    )
    return LocalEvidenceAnalysisRequest(
        analysis_id=analysis_id,
        ticker=ticker.upper().strip(),
        evidence_fingerprint=fingerprint,
        evidence_events=normalized,
        source_refs=refs,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


class LocalEvidenceQueue:
    """Filesystem-backed, idempotent queue for rebuildable local analysis."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.queue_dir = self.root / "queue"
        self.runs_dir = self.root / "runs"
        self.latest_dir = self.root / "latest"
        self.manifests_dir = self.root / "manifests"
        for path in (
            self.queue_dir,
            self.runs_dir,
            self.latest_dir,
            self.manifests_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def enqueue(
        self,
        ticker: str,
        evidence_events: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    ) -> QueueEnqueueResult:
        request = build_request(ticker, evidence_events)
        queued_path = self.queue_dir / f"{request.analysis_id}.json"
        run_path = self.runs_dir / f"{request.analysis_id}.json"

        if run_path.exists():
            previous = json.loads(run_path.read_text(encoding="utf-8"))
            if previous.get("status") != LocalAnalysisStatus.FAILED.value or "RETRY_EXHAUSTED" in previous.get("quality_flags", []):
                return QueueEnqueueResult(
                    request=request,
                    queue_status="ALREADY_PROCESSED",
                )
        if queued_path.exists():
            return QueueEnqueueResult(request=request, queue_status="ALREADY_QUEUED")

        _atomic_json_write(
            queued_path,
            {
                **request.as_dict(),
                "status": LocalAnalysisStatus.PENDING.value,
            },
        )
        return QueueEnqueueResult(request=request, queue_status="ENQUEUED")

    def pending(self, *, limit: int | None = None) -> list[LocalEvidenceAnalysisRequest]:
        paths = sorted(self.queue_dir.glob("*.json"))
        requests: list[LocalEvidenceAnalysisRequest] = []
        now = datetime.now(timezone.utc)
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            due = payload.get("next_attempt_at")
            if due and datetime.fromisoformat(due) > now:
                continue
            if payload.get("status") == LocalAnalysisStatus.RUNNING.value:
                started = datetime.fromisoformat(payload["started_at"])
                if now - started < timedelta(minutes=20):
                    continue
            requests.append(LocalEvidenceAnalysisRequest.from_dict(payload))
            if limit is not None and len(requests) >= max(0, int(limit)):
                break
        if limit is not None and limit <= 0:
            return []
        return requests

    def mark_running(self, request: LocalEvidenceAnalysisRequest) -> None:
        path = self.queue_dir / f"{request.analysis_id}.json"
        previous = json.loads(path.read_text())
        _atomic_json_write(
            path,
            {
                **previous,
                **request.as_dict(),
                "status": LocalAnalysisStatus.RUNNING.value,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def defer(self, request: LocalEvidenceAnalysisRequest, *, reason: str, runtime_failure: bool = False, model: str = "") -> bool:
        path = self.queue_dir / f"{request.analysis_id}.json"
        previous = json.loads(path.read_text())
        attempts = int(previous.get("runtime_failures", 0)) + int(runtime_failure)
        now = datetime.now(timezone.utc)
        if attempts >= 3:
            dossier = self.fail(request, error=reason, model=model)
            from dataclasses import replace
            self.complete(replace(dossier, quality_flags=("MODEL_FAILURE", "RETRY_EXHAUSTED")))
            return False
        _atomic_json_write(
            path,
            {
                **request.as_dict(),
                "status": LocalAnalysisStatus.PENDING.value,
                "deferred_at": now.isoformat(),
                "defer_reason": reason,
                "runtime_failures": attempts,
                "next_attempt_at": (now + timedelta(seconds=60 * 2 ** attempts)).isoformat(),
            },
        )
        return True

    def outstanding_count(self) -> int:
        return sum(1 for _ in self.queue_dir.glob("*.json"))

    def complete(self, dossier: LocalEvidenceDossier) -> None:
        payload = dossier.as_dict()
        _atomic_json_write(self.runs_dir / f"{dossier.analysis_id}.json", payload)
        _atomic_json_write(self.latest_dir / f"{dossier.ticker}.json", payload)
        (self.queue_dir / f"{dossier.analysis_id}.json").unlink(missing_ok=True)

    def fail(
        self,
        request: LocalEvidenceAnalysisRequest,
        *,
        error: str,
        model: str,
    ) -> LocalEvidenceDossier:
        dossier = LocalEvidenceDossier(
            analysis_id=request.analysis_id,
            ticker=request.ticker,
            evidence_fingerprint=request.evidence_fingerprint,
            evidence_refs=request.source_refs,
            created_at=datetime.now(timezone.utc).isoformat(),
            model=model,
            prompt_version=request.prompt_version,
            status=LocalAnalysisStatus.FAILED,
            quality_flags=("MODEL_FAILURE",),
            analysis={"error": error},
        )
        self.complete(dossier)
        return dossier

    def latest(self, ticker: str) -> LocalEvidenceDossier | None:
        path = self.latest_dir / f"{ticker.upper().strip()}.json"
        if not path.exists():
            return None
        return LocalEvidenceDossier.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )


class LocalEvidenceAnalyst:
    def __init__(self, client: OllamaClient | None = None):
        self.client = client or OllamaClient(
            model=os.getenv("B3_LOCAL_EVIDENCE_MODEL", "qwen3:4b-instruct-2507-q4_K_M"),
            think=False, format_schema=LOCAL_ANALYSIS_SCHEMA,
            num_ctx=int(os.getenv("B3_LOCAL_EVIDENCE_NUM_CTX", "4096")),
            num_predict=int(os.getenv("B3_LOCAL_EVIDENCE_NUM_PREDICT", "2048")),
            timeout=float(os.getenv("B3_LOCAL_EVIDENCE_TIMEOUT_SECONDS", "600")),
        )

    def analyze(self, request: LocalEvidenceAnalysisRequest) -> LocalEvidenceDossier:
        prompt = _analysis_prompt(request)
        client = self.client
        if isinstance(client, OllamaClient):
            schema = deepcopy(LOCAL_ANALYSIS_SCHEMA)
            refs_schema = schema["properties"]["evidence_refs"]
            if request.source_refs:
                refs_schema["items"]["enum"] = list(request.source_refs)
            else:
                refs_schema["maxItems"] = 0
            client = OllamaClient(
                base_url=client.base_url, model=client.model,
                timeout=client.timeout, num_ctx=client.num_ctx,
                num_predict=client.num_predict, keep_alive=client.keep_alive,
                think=client.think, format_schema=schema,
            )
        result = client.ask(prompt)
        quality_flags: list[str] = []

        analysis: dict[str, Any] | None
        try:
            analysis = _extract_json_object(result.content)
        except ValueError:
            analysis = None
            quality_flags.append("INVALID_JSON")

        if result.eval_count is not None and result.eval_count >= self.client.num_predict:
            quality_flags.append("OUTPUT_LIMIT_REACHED")

        if not result.content.strip():
            quality_flags.append("MISSING_CONTENT")

        if analysis is not None:
            required = {
                "summary": str,
                "risks": list,
                "catalysts": list,
                "contradictions": list,
                "questions_for_senior_review": list,
                "escalation_recommended": bool,
                "evidence_refs": list,
            }
            if any(
                key not in analysis or not isinstance(analysis.get(key), expected)
                for key, expected in required.items()
            ):
                quality_flags.append("INVALID_SCHEMA")
            if set(analysis) - set(required) or any(
                not isinstance(analysis.get(key), list)
                or any(not isinstance(item, str) for item in analysis[key])
                for key, expected in required.items() if expected is list
            ):
                quality_flags.append("INVALID_SCHEMA")

            if isinstance(analysis.get("summary"), str) and len(analysis["summary"]) > 400:
                quality_flags.append("OUTPUT_TOO_VERBOSE")
            for key in ("risks", "catalysts", "contradictions", "questions_for_senior_review"):
                values = analysis.get(key)
                if isinstance(values, list) and (
                    len(values) > 2 or any(isinstance(item, str) and len(item) > 200 for item in values)
                ):
                    quality_flags.append("OUTPUT_TOO_VERBOSE")

            refs = analysis.get("evidence_refs")
            if not isinstance(refs, list):
                quality_flags.append("UNKNOWN_EVIDENCE_REF")
            else:
                allowed = set(request.source_refs)
                if not set(str(item) for item in refs).issubset(allowed):
                    quality_flags.append("UNKNOWN_EVIDENCE_REF")

        status = (
            LocalAnalysisStatus.READY
            if not quality_flags
            else LocalAnalysisStatus.DEGRADED
        )
        return LocalEvidenceDossier(
            analysis_id=request.analysis_id,
            ticker=request.ticker,
            evidence_fingerprint=request.evidence_fingerprint,
            evidence_refs=request.source_refs,
            created_at=datetime.now(timezone.utc).isoformat(),
            model=result.model,
            prompt_version=request.prompt_version,
            status=status,
            quality_flags=tuple(dict.fromkeys(quality_flags)),
            analysis=analysis,
            raw_analysis=result.content,
            thinking_chars=len(result.thinking),
            input_chars=len(prompt),
            eval_count=result.eval_count,
            num_predict=self.client.num_predict,
            total_duration_ns=result.total_duration_ns,
        )


@dataclass(frozen=True, slots=True)
class LocalContextSelection:
    dossier: LocalEvidenceDossier | None
    status: str
    reasons: tuple[str, ...] = field(default_factory=tuple)


class LocalEvidenceContextSelector:
    """Non-blocking selector for optional local dossier reuse."""

    def __init__(
        self,
        queue: LocalEvidenceQueue,
        *,
        max_age: timedelta = timedelta(days=3),
    ):
        self.queue = queue
        self.max_age = max_age

    def select(
        self,
        *,
        ticker: str,
        evidence_events: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        as_of: datetime | None = None,
    ) -> LocalContextSelection:
        request=build_request(ticker,evidence_events)
        matching_path=self.queue.runs_dir / f"{request.analysis_id}.json"
        dossier = LocalEvidenceDossier.from_dict(json.loads(matching_path.read_text(encoding="utf-8"))) if matching_path.exists() else self.queue.latest(ticker)
        if dossier is None:
            return LocalContextSelection(None, "ABSENT", ("NO_DOSSIER",))

        expected = evidence_fingerprint(ticker, evidence_events)
        reasons: list[str] = []
        if dossier.evidence_fingerprint != expected:
            reasons.append("STALE_EVIDENCE")
        if dossier.status != LocalAnalysisStatus.READY:
            reasons.append(f"STATUS_{dossier.status.value}")
        if dossier.quality_flags:
            reasons.extend(dossier.quality_flags)

        now = as_of or datetime.now(timezone.utc)
        try:
            created_at = datetime.fromisoformat(dossier.created_at)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if now - created_at > self.max_age:
                reasons.append("STALE_DOSSIER")
        except ValueError:
            reasons.append("STALE_DOSSIER")

        if reasons:
            return LocalContextSelection(None, "OMITTED", tuple(dict.fromkeys(reasons)))
        return LocalContextSelection(dossier, "READY")


def _analysis_prompt(request: LocalEvidenceAnalysisRequest) -> str:
    return (
        "You are the B3 V4.3 local asynchronous Evidence Analyst. "
        "Analyze only the supplied canonical evidence. Do not invent prices, "
        "share classes, returns, probabilities, causal claims or facts. "
        "Do not make an investment recommendation. If evidence does not support "
        "a conclusion, state that limitation. Return ONLY one compact JSON object "
        "matching the runtime-enforced JSON schema. Summary: at most 400 characters. "
        "Each analytical list: at most two items, each at most 200 characters. "
        "Use empty lists when unsupported. Select only material issues; flag escalation "
        "when the bundle requires a fuller senior review."
        f"\nTicker: {request.ticker}"
        "\nAllowed evidence refs: "
        + json.dumps(list(request.source_refs), ensure_ascii=False)
        + "\nCanonical evidence events: "
        + json.dumps(list(request.evidence_events), ensure_ascii=False)
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    clean = text.strip()
    fence = chr(96) * 3
    candidates = [clean]
    if fence in clean:
        for block in clean.split(fence):
            candidate = block.strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            if candidate:
                candidates.append(candidate)
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        candidates.append(clean[start : end + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("local Evidence analyst did not return a JSON object")


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temp.replace(path)
