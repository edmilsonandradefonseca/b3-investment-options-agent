from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from b3_agent.llm.ollama_client import OllamaClient


@dataclass(frozen=True, slots=True)
class OllamaPreflightResult:
    model: str
    installed_models: tuple[str, ...]
    loaded_models_before: tuple[str, ...]
    loaded_models_after: tuple[str, ...]
    elapsed_seconds: float
    response: str
    load_duration_ns: int | None
    prompt_eval_count: int | None
    eval_count: int | None
    eval_duration_ns: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "installed_models": list(self.installed_models),
            "loaded_models_before": list(self.loaded_models_before),
            "loaded_models_after": list(self.loaded_models_after),
            "elapsed_seconds": self.elapsed_seconds,
            "response": self.response,
            "load_duration_ns": self.load_duration_ns,
            "prompt_eval_count": self.prompt_eval_count,
            "eval_count": self.eval_count,
            "eval_duration_ns": self.eval_duration_ns,
        }


def ollama_preflight(
    *,
    client: OllamaClient | None = None,
    warm_timeout: float = 180.0,
) -> OllamaPreflightResult:
    """Validate Ollama/model availability and warm the model with bounded work.

    The warmup disables thinking only for this tiny health request and leaves
    the model resident for five minutes. The subsequent real reasoning request
    can use normal thinking and sets keep_alive=0 to unload after inference.
    """
    base = client or OllamaClient()
    installed = _model_names(_get_json(f"{base.base_url}/api/tags", timeout=15.0))
    if not _model_available(base.model, installed):
        raise RuntimeError(
            f"Ollama model is not installed: {base.model}; "
            f"installed={','.join(installed) or 'none'}"
        )

    before = _model_names(_get_json(f"{base.base_url}/api/ps", timeout=15.0))
    warm = OllamaClient(
        base_url=base.base_url,
        model=base.model,
        timeout=min(float(warm_timeout), base.timeout),
        num_ctx=512,
        num_predict=24,
        keep_alive="5m",
        think=False,
    )

    started = time.monotonic()
    result = warm.ask("Reply exactly READY.")
    elapsed = time.monotonic() - started
    after = _model_names(_get_json(f"{base.base_url}/api/ps", timeout=15.0))

    return OllamaPreflightResult(
        model=result.model,
        installed_models=installed,
        loaded_models_before=before,
        loaded_models_after=after,
        elapsed_seconds=round(elapsed, 3),
        response=result.content[:120],
        load_duration_ns=result.load_duration_ns,
        prompt_eval_count=result.prompt_eval_count,
        eval_count=result.eval_count,
        eval_duration_ns=result.eval_duration_ns,
    )


def _get_json(url: str, *, timeout: float) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(
            f"Ollama runtime probe failed url={url}: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Ollama runtime probe returned invalid payload: {url}")
    return payload


def _model_names(payload: dict[str, Any]) -> tuple[str, ...]:
    raw = payload.get("models") or ()
    names: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            value = str(item.get("name") or item.get("model") or "").strip()
            if value and value not in names:
                names.append(value)
    return tuple(names)


def _model_available(model: str, installed: tuple[str, ...]) -> bool:
    if model in installed:
        return True
    if ":" not in model and f"{model}:latest" in installed:
        return True
    return False
