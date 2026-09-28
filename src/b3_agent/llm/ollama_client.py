from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class OllamaResult:
    model: str
    content: str
    thinking: str
    total_duration_ns: int | None
    eval_count: int | None
    eval_duration_ns: int | None


class OllamaClient:
    def __init__(self, *, base_url: str | None = None, model: str | None = None, timeout: float = 240.0) -> None:
        self.base_url = (base_url or os.getenv("B3_OLLAMA_URL") or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or os.getenv("B3_LOCAL_REASONING_MODEL") or "deepseek-r1:8b"
        self.timeout = timeout

    def ask(self, prompt: str) -> OllamaResult:
        clean = prompt.strip()
        if not clean:
            raise ValueError("prompt must not be empty")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": clean}],
            "stream": False,
            "options": {"temperature": 0},
        }
        req = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        message: dict[str, Any] = body.get("message") or {}
        content = str(message.get("content") or "").strip()
        if not content:
            raise RuntimeError("Ollama returned empty content")
        return OllamaResult(
            model=str(body.get("model") or self.model),
            content=content,
            thinking=str(message.get("thinking") or ""),
            total_duration_ns=_as_int(body.get("total_duration")),
            eval_count=_as_int(body.get("eval_count")),
            eval_duration_ns=_as_int(body.get("eval_duration")),
        )


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
