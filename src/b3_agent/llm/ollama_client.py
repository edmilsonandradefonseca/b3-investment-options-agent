from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from b3_agent.llm.host_lock import local_reasoning_lock


@dataclass(frozen=True, slots=True)
class OllamaResult:
    model: str
    content: str
    thinking: str
    total_duration_ns: int | None
    load_duration_ns: int | None
    prompt_eval_count: int | None
    prompt_eval_cached_count: int | None
    prompt_eval_duration_ns: int | None
    eval_count: int | None
    eval_duration_ns: int | None


class OllamaClient:
    """Bounded stdlib-only Ollama client for local/background reasoning."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
        keep_alive: str | int | None = None,
        think: bool | None = None,
        format_schema: dict[str, Any] | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("B3_OLLAMA_URL")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = (
            model
            or os.getenv("B3_LOCAL_REASONING_MODEL")
            or "deepseek-r1:8b"
        )
        self.timeout = (
            float(os.getenv("B3_OLLAMA_TIMEOUT_SECONDS", "300"))
            if timeout is None
            else float(timeout)
        )
        self.num_ctx = (
            int(os.getenv("B3_OLLAMA_NUM_CTX", "2048"))
            if num_ctx is None
            else int(num_ctx)
        )
        self.num_predict = (
            int(os.getenv("B3_OLLAMA_NUM_PREDICT", "768"))
            if num_predict is None
            else int(num_predict)
        )
        raw_keep_alive = (
            os.getenv("B3_OLLAMA_KEEP_ALIVE", "0")
            if keep_alive is None
            else keep_alive
        )
        self.keep_alive: str | int = (
            int(raw_keep_alive)
            if isinstance(raw_keep_alive, str)
            and raw_keep_alive.strip().lstrip("-").isdigit()
            else raw_keep_alive
        )
        self.think = think
        self.format_schema = dict(format_schema) if format_schema is not None else None

        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.num_ctx < 256:
            raise ValueError("num_ctx must be at least 256")
        if self.num_predict < 1:
            raise ValueError("num_predict must be positive")

    def ask(self, prompt: str) -> OllamaResult:
        clean = prompt.strip()
        if not clean:
            raise ValueError("prompt must not be empty")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": clean}],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
        }
        if self.think is not None:
            payload["think"] = self.think
        if self.format_schema is not None:
            payload["format"] = self.format_schema

        req = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with local_reasoning_lock():
                body = self._post(req)
        except HTTPError as exc:
            detail = _http_error_detail(exc)
            if (
                exc.code == 400
                and self.think is not None
                and "think" in detail.casefold()
            ):
                compatibility_payload = dict(payload)
                compatibility_payload.pop("think", None)
                compatibility_req = Request(
                    f"{self.base_url}/api/chat",
                    data=json.dumps(compatibility_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with local_reasoning_lock():
                        body = self._post(compatibility_req)
                except (HTTPError, URLError, TimeoutError, OSError) as retry_exc:
                    retry_detail = (
                        _http_error_detail(retry_exc)
                        if isinstance(retry_exc, HTTPError)
                        else str(retry_exc)
                    )
                    raise RuntimeError(
                        "Ollama request failed after think compatibility retry "
                        f"model={self.model} timeout_s={self.timeout:g} "
                        f"num_ctx={self.num_ctx} num_predict={self.num_predict}: "
                        f"{type(retry_exc).__name__}: {retry_detail}"
                    ) from retry_exc
            else:
                raise RuntimeError(
                    "Ollama request failed "
                    f"model={self.model} timeout_s={self.timeout:g} "
                    f"num_ctx={self.num_ctx} num_predict={self.num_predict}: "
                    f"HTTPError {exc.code}: {detail}"
                ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                "Ollama request failed "
                f"model={self.model} timeout_s={self.timeout:g} "
                f"num_ctx={self.num_ctx} num_predict={self.num_predict}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        message: dict[str, Any] = body.get("message") or {}
        content = str(message.get("content") or "").strip()
        if not content:
            raise RuntimeError("Ollama returned empty content")
        return OllamaResult(
            model=str(body.get("model") or self.model),
            content=content,
            thinking=str(message.get("thinking") or ""),
            total_duration_ns=_as_int(body.get("total_duration")),
            load_duration_ns=_as_int(body.get("load_duration")),
            prompt_eval_count=_as_int(body.get("prompt_eval_count")),
            prompt_eval_cached_count=_as_int(body.get("prompt_eval_cached_count")),
            prompt_eval_duration_ns=_as_int(body.get("prompt_eval_duration")),
            eval_count=_as_int(body.get("eval_count")),
            eval_duration_ns=_as_int(body.get("eval_duration")),
        )

    def _post(self, req: Request) -> dict[str, Any]:
        with urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def _http_error_detail(exc: HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        raw = ""
    return raw[:1000] or str(exc)


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
